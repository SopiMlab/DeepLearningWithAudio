import java.util.*;

import blobDetection.*;
import kinect4WinSDK.Kinect;
import oscP5.*;
import netP5.*;

final int kWidth = 640;
final int kHeight = 480;
final int maxBlobs = 1000;
final float lagTimeConstant = 0.3;
final String oscCtrlHost = "10.100.7.104";
final int oscCtrlPort = 9000;
final String oscHost = "193.167.1.218";
final int oscPort = 12001;
final int gridSize = 9;
final float glitchDetectThreshold = 0.2; 
Kinect kinect;
PGraphics detectG;
PGraphics maskViewG;
PGraphics depthViewG;
PShader colorMaskShader;
PShader maskViewShader;
PShader depthViewShader;
PShader medianShader;
PShader multiplyShader;
PImage mask1;
PImage mask2;
BlobDetection blobDetector1;
BlobDetection blobDetector2;
Blob[] blobs1 = new Blob[maxBlobs];
Blob[] blobs2 = new Blob[maxBlobs];
Blob[] blobsTemp1 = new Blob[maxBlobs];
Blob[] blobsTemp2 = new Blob[maxBlobs];
int blobCount1 = 0;
int blobCount2 = 0;
int blobCountTemp1 = 0;
int blobCountTemp2 = 0;
int[] depthSampleXs;
int[] depthSampleYs;
OscP5 oscP5;
NetAddress oscCtrlDest;
NetAddress oscDest;
LinkedHashMap<String, String> paramNames;
HashMap<String, String> paramNamesInv;
HashMap<String, Float> params;
String paramsFile = "params.txt";
float lastTime = 0.0;
float time = 0.0;
ExpLag xLag;
ExpLag zLag;
int col = -1;
int row = 1;
float depthXScale;
float depthXTranslate;
float depthYScale;
float depthYTranslate;
float lastX = -1.0;
float lastZ = -1.0;

void setup() {
  size(1280, 960, P3D);

  kinect = new Kinect(this);
  detectG = createGraphics(kWidth, kHeight, P3D);
  maskViewG = createGraphics(kWidth, kHeight, P3D);
  depthViewG = createGraphics(kWidth, kHeight, P3D);
  colorMaskShader = loadShader("colormask.frag");
  maskViewShader = loadShader("maskview.frag");
  depthViewShader = loadShader("depthview.frag");
  medianShader = loadShader("median.frag");
  multiplyShader = loadShader("multiply.frag");

  detectG.beginDraw();
  detectG.noStroke();
  detectG.fill(255);
  detectG.endDraw();

  maskViewG.beginDraw();
  maskViewG.noStroke();
  maskViewG.fill(255);
  maskViewG.endDraw();

  depthViewG.beginDraw();
  depthViewG.noStroke();
  depthViewG.fill(255);
  depthViewG.endDraw();

  BlobDetection.setConstants(maxBlobs, 4000, 500);
  blobDetector1 = new BlobDetection(kWidth, kHeight);
  blobDetector1.setPosDiscrimination(true);
  blobDetector2 = new BlobDetection(kWidth, kHeight);
  blobDetector2.setPosDiscrimination(true);
  
  depthSampleXs = new int[] {0, 2, -2, 0, 0};
  depthSampleYs = new int[] {0, 0, 0, 2, -2};
  
  oscP5 = new OscP5(this, 12000);
  oscCtrlDest = new NetAddress(oscCtrlHost, oscCtrlPort);
  oscDest = new NetAddress(oscHost, oscPort);

  paramNames = new LinkedHashMap<String, String>();
  paramNames.put("/1/fader1", "target1HueMin");
  paramNames.put("/1/fader2", "target1HueMax");
  paramNames.put("/1/fader3", "target1SatMin");
  paramNames.put("/1/fader4", "target1SatMax");
  paramNames.put("/1/fader5", "target1LightMin");
  paramNames.put("/1/fader6", "target1LightMax");
  paramNames.put("/2/fader7", "target2HueMin");
  paramNames.put("/2/fader8", "target2HueMax");
  paramNames.put("/2/fader9", "target2SatMin");
  paramNames.put("/2/fader10", "target2SatMax");
  paramNames.put("/2/fader11", "target2LightMin");
  paramNames.put("/2/fader12", "target2LightMax");
  paramNames.put("/3/fader13", "blobSizeMin");
  paramNames.put("/3/fader14", "blobSizeMax");
  paramNames.put("/3/fader15", "blobFillMin");
  paramNames.put("/3/fader16", "blobExpand");
  paramNames.put("/4/fader17", "nearWidth");
  paramNames.put("/4/fader18", "farWidth");
  paramNames.put("/4/fader19", "nearZ");
  paramNames.put("/4/fader20", "farZ");
  paramNames.put("/4/fader21", "stickGrow");
  paramNames.put("/5/fader23", "depthXScale");
  paramNames.put("/5/fader24", "depthXTranslate");
  paramNames.put("/5/fader25", "depthYScale");
  paramNames.put("/5/fader26", "depthYTranslate");

  
  paramNamesInv = new HashMap<String, String>();
  for(Map.Entry<String, String> entry : paramNames.entrySet()) {
    paramNamesInv.put(entry.getValue(), entry.getKey());
  }
  
  params = new HashMap<String, Float>();
  loadParams();

  xLag = new ExpLag(lagTimeConstant);
  zLag = new ExpLag(lagTimeConstant);

  textAlign(LEFT, TOP);
  
  frameRate(30);
}

class ExpLag {
  public float timeConstant;
  public float value = 0.0;
  public float lastInput = 0.0;
  public boolean isFirst = true;
  
  public ExpLag(float timeConstant) {
    this.timeConstant = timeConstant;
  }
  
  public boolean update(float deltaTime) {
    return !this.isFirst && this.update(deltaTime, this.lastInput);
  }
  
  public boolean update(float deltaTime, float input) {
    float newValue;
    if(this.isFirst) {
      newValue = input;
      this.isFirst = false;
    } else {
      float diff = deltaTime * (input - this.value) / this.timeConstant; 
      newValue = this.value + diff;
    }
    
    this.value = newValue;
    this.lastInput = input;
    return true;
  }
  
  public float getValue() {
    return this.value;
  }
}

void loadParams() {
  params.clear();
  for(Map.Entry<String, String> entry : paramNames.entrySet()) {
    params.put(entry.getValue(), 0.0);
  }
  
  String[] strings = loadStrings(paramsFile);
  if(strings != null) {
    int paramCount = strings.length / 2;
    for(int i = 0; i < paramCount; i++) {
      String name = strings[i*2];
      float value = Float.parseFloat(strings[i*2+1]);
      if(params.containsKey(name)) {
        params.put(name, value);
      }
    }
  }
  
  for(Map.Entry<String, String> entry : paramNames.entrySet()) {
    String addr = entry.getKey();
    String name = entry.getValue();
    OscMessage ctrlMsg = new OscMessage(addr);
    ctrlMsg.add(params.get(name));
    oscP5.send(ctrlMsg, oscCtrlDest); 
  }
}

void saveParams() {
  String[] strings = new String[paramNames.size()*2];
  int i = 0;
  for(Map.Entry<String, String> entry : paramNames.entrySet()) {
    String name = entry.getValue();
    strings[i*2] = name;
    strings[i*2+1] = "" + params.get(name);
    i++;
  }
  saveStrings(paramsFile, strings);
}

float getFillDegree(Blob b, PImage img) {
  int fillCount = 0;
  for(int y = 0; y < img.height; y++) {
    for(int x = 0; x < img.width; x++) {
      color c = img.get(round(b.xMin*img.width)+x, round(b.yMin*img.height)+y);
      if(red(c) > 0) {
        fillCount++;
      }
    }
  }
  return float(fillCount) / (b.w*img.width*b.h*img.height);
}

void detect(PImage image) {
  int medianPasses = 1;
  
  PImage medianImage = image;
  for(int i = 0; i < medianPasses; i++) {
    detectG.beginDraw();
    detectG.shader(medianShader);
    medianShader.set("resolution", kWidth, kHeight);
    medianShader.set("image", medianImage);
    detectG.rect(0, 0, kWidth, kHeight);
    detectG.endDraw();
    medianImage = detectG.copy();
  }
  
  detectG.beginDraw();
  detectG.shader(colorMaskShader);
  colorMaskShader.set("resolution", kWidth, kHeight);
  colorMaskShader.set("image", medianImage);
  colorMaskShader.set("target_hsl_min",
    params.get("target1HueMin"),
    params.get("target1SatMin"),
    params.get("target1LightMin")
  );
  colorMaskShader.set("target_hsl_max",
    params.get("target1HueMax"),
    params.get("target1SatMax"),
    params.get("target1LightMax")
  );
  detectG.rect(0, 0, kWidth, kHeight);
  detectG.endDraw();
  
  mask1 = detectG.copy();

  detectG.beginDraw();
  detectG.shader(colorMaskShader);
  colorMaskShader.set("resolution", kWidth, kHeight);
  colorMaskShader.set("image", medianImage);
  colorMaskShader.set("target_hsl_min",
    params.get("target2HueMin"),
    params.get("target2SatMin"),
    params.get("target2LightMin")
  );
  colorMaskShader.set("target_hsl_max",
    params.get("target2HueMax"),
    params.get("target2SatMax"),
    params.get("target2LightMax")
  );
  detectG.rect(0, 0, kWidth, kHeight);
  detectG.endDraw();
  
  mask2 = detectG.copy();
    
  float aspectInv = float(height)/width;
  float blobWidthMin = params.get("blobSizeMin");
  float blobWidthMax = params.get("blobSizeMax");
  float blobHeightMin = blobWidthMin*aspectInv;
  float blobHeightMax = blobWidthMax*aspectInv;

  blobDetector1.computeBlobs(mask1.pixels);
  blobDetector2.computeBlobs(mask2.pixels);
  
  float blobFillMin = params.get("blobFillMin");
  float blobExpand = params.get("blobExpand");
  float wExp = 1.0 + blobExpand;
  float hExp = wExp*aspectInv;
  /*float wExpFactor = blobExpand*kWidth;
  float hExpFactor = blobExpand*kHeight;

  detectG.beginDraw();
  detectG.resetShader();
  detectG.ellipseMode(CENTER);
  detectG.background(0);*/
  blobCount1 = 0;  
  for(int i = 0; i < blobDetector1.getBlobNb(); i++) {
    Blob b = blobDetector1.getBlob(i);
    
    if(
      blobWidthMin <= b.w && b.w <= blobWidthMax &&
      blobHeightMin <= b.h && b.h <= blobHeightMax &&
      blobFillMin <= getFillDegree(b, mask1)
    ) {
      /*detectG.ellipse(
        b.x*kWidth,
        b.y*kHeight,
        b.w*wExpFactor,
        b.h*hExpFactor
      );*/
      
      blobs1[blobCount1] = b;
      blobCount1++;
    }
  }
  detectG.endDraw();
  
  //PImage expImage1 = detectG.copy();
  
  /*detectG.beginDraw();
  detectG.background(0);*/
  blobCount2 = 0;
  for(int i = 0; i < blobDetector2.getBlobNb(); i++) {
    Blob b = blobDetector2.getBlob(i);
    
    if(
      blobWidthMin <= b.w && b.w <= blobWidthMax &&
      blobHeightMin <= b.h && b.h <= blobHeightMax &&
      blobFillMin <= getFillDegree(b, mask2)
    ) {
      /*detectG.ellipse(
        b.x*kWidth,
        b.y*kHeight,
        b.w*wExpFactor,
        b.h*hExpFactor
      );*/
      blobs2[blobCount2] = b;
      blobCount2++;
    }
  }
  /*detectG.ellipseMode(CORNER);
  detectG.endDraw();
  
  PImage expImage2 = detectG.copy();
  
  detectG.beginDraw();
  detectG.shader(multiplyShader);
  multiplyShader.set("image1", expImage1);
  multiplyShader.set("image2", expImage2);
  detectG.rect(0, 0, kWidth, kHeight);
  detectG.endDraw();*/
  
  // remove blobs that are close to less than 2 of the other color
  blobCountTemp1 = 0;
  for(int i = 0; i < blobCount1; i++) {
    Blob b1 = blobs1[i];
    float wExp1 = b1.w * wExp;
    float hExp1 = b1.h * hExp;
    
    int closeCount = 0;
    for(int j = 0; j < blobCount2; j++) {
      Blob b2 = blobs2[j];
      float wExp2 = b2.w * wExp;
      float hExp2 = b2.h * hExp;

      float dx = abs(b1.x - b2.x);
      float dy = abs(b1.y - b2.y);
      
      boolean close = dx < 0.5*(wExp1 + wExp2) && dy < 0.5*(hExp1 + hExp2);
      
      if(close) {
        closeCount++;
      }
    }
    if(closeCount >= 2) {
      blobsTemp1[blobCountTemp1] = b1;
      blobCountTemp1++;
    }
  }
  
  blobCountTemp2 = 0;
  for(int i = 0; i < blobCount2; i++) {
    Blob b2 = blobs2[i];
    float wExp2 = b2.w * wExp;
    float hExp2 = b2.h * hExp;
    
    int closeCount = 0;
    for(int j = 0; j < blobCount1; j++) {
      Blob b1 = blobs1[j];
      float wExp1 = b1.w * wExp;
      float hExp1 = b1.h * hExp;

      float dx = abs(b1.x - b2.x);
      float dy = abs(b1.y - b2.y);
      
      boolean close = dx < 0.5*(wExp1 + wExp2) && dy < 0.5*(hExp1 + hExp2);
      
      if(close) {
        closeCount++;
      }
    }
    if(closeCount >= 2) {
      blobsTemp2[blobCountTemp2] = b2;
      blobCountTemp2++;
    }
  }
  
  Blob[] blobsSwap1 = blobs1;
  blobs1 = blobsTemp1;
  blobsTemp1 = blobsSwap1;
  blobCount1 = blobCountTemp1;

  Blob[] blobsSwap2 = blobs2;
  blobs2 = blobsTemp2;
  blobsTemp2 = blobsSwap2;
  blobCount2 = blobCountTemp2;  
}

void draw() {
  lastTime = time;
  time = millis();
  
  depthXScale = map(params.get("depthXScale"), 0.0, 1.0, 0.5, 2.0);
  depthXTranslate = map(params.get("depthXTranslate"), 0.0, 1.0, -50.0, 50.0);
  depthYScale = map(params.get("depthYScale"), 0.0, 1.0, 0.5, 2.0);
  depthYTranslate = map(params.get("depthYTranslate"), 0.0, 1.0, -50.0, 50.0);

  
  fill(255);
  noStroke();
  ellipseMode(CORNER);

  background(0);
  PImage image = kinect.GetImage();
  PImage depth = kinect.GetDepth();

  image(image, 0, 0, width*0.5, height*0.5);
  
  depthViewG.beginDraw();
  depthViewG.shader(depthViewShader);
  depthViewShader.set("resolution", width, height);
  depthViewShader.set("depthImage", depth);
  depthViewShader.set("colorImage", image);
  depthViewShader.set("nearZ", params.get("nearZ"));
  depthViewShader.set("farZ", params.get("farZ"));
  depthViewShader.set("xScale", depthXScale);
  depthViewShader.set("xTranslate", depthXTranslate);
  depthViewShader.set("yScale", depthYScale);
  depthViewShader.set("yTranslate", depthYTranslate);
  depthViewG.rect(0, 0, kWidth, kHeight);
  depthViewG.endDraw();
  image(depthViewG, width*0.5, 0, width*0.5, height*0.5);
    
  detect(image);

  float x = -1.0;
  float y = -1.0;
  float z = -1.0;
  float mx = -1.0;
  float mz = -1.0;

  float deltaTime = (time - lastTime) * 0.001;
  boolean xUpdated = false;
  boolean zUpdated = false;

  int n = blobCount1 + blobCount2;
  if(n > 0) {
    x = 0.0;
    y = 0.0;
    float tempZ = 0.0;
    
    int zAdded = 0;
    for(int i = 0; i < blobCount1; i++) {
      Blob b = blobs1[i];
      x += b.x;
      y += b.y;
      for(int j = 0; j < depthSampleXs.length; j++) {
        int dsx = round(b.x*kWidth*depthXScale + depthXTranslate)
          + depthSampleXs[j];
        int dsy = round(b.y*kHeight*depthYScale + depthYTranslate)
          + depthSampleYs[j];
        float zVal = red(depth.get(dsx, dsy))/255;
        if(zVal > 0.0) {
          tempZ += zVal;
          zAdded++;
        }
      }
    }
    for(int i = 0; i < blobCount2; i++) {
      Blob b = blobs2[i];
      x += b.x;
      y += b.y;
      for(int j = 0; j < depthSampleXs.length; j++) {
        int dsx = round(b.x*kWidth*depthXScale + depthXTranslate)
          + depthSampleXs[j];
        int dsy = round(b.y*kHeight*depthYScale + depthYTranslate)
          + depthSampleYs[j];
        float zVal = red(depth.get(dsx, dsy))/255;
        if(zVal > 0.0) {
          tempZ += zVal;
          zAdded++;
        }
      }
    }

    x /= n;
    y /= n;
    if(zAdded > 0) {
      z = tempZ/zAdded;
    }
  }
   
  if(z >= 0.0) {
    float nearZ = params.get("nearZ");
    float farZ = params.get("farZ");
    
    mz = max(0.0, min(1.0, map(z, nearZ, farZ, 0.0, 1.0)));
    
    float nearW = params.get("nearWidth");
    float farW = params.get("farWidth");
    float w = map(mz, 0.0, 1.0, nearW, farW);
    float tempX = map(x, 0.5-0.5*w, 0.5+0.5*w, 0.0, 1.0);
    mx = max(0.0, min(1.0, tempX));
  }
  
  
  if(mx >= 0.0 && mz >= 0.0) {
    float distMoved = sqrt(pow(mx - lastX, 2.0) + pow(mz - lastZ, 2.0));

    lastX = mx;
    lastZ = mz;

    if(distMoved > glitchDetectThreshold) {
      mx = -1.0;
      mz = -1.0;
    }
  }
    
  xUpdated = mx >= 0.0 ? xLag.update(deltaTime, mx) : xLag.update(deltaTime);
  zUpdated = mz >= 0.0 ? zLag.update(deltaTime, mz) : zLag.update(deltaTime);
  
  if(xUpdated || zUpdated) {
    float xVal = xLag.getValue();
    float zVal = zLag.getValue();
    
    float stickGrow = params.get("stickGrow");
    float stickXMin = (col - stickGrow*0.5)/gridSize;
    float stickXMax = (col + 1.0 + stickGrow*0.5)/gridSize;
    float stickZMin = (row - stickGrow*0.5)/gridSize;
    float stickZMax = (row + 1.0 + stickGrow*0.5)/gridSize;
    boolean inStickX = stickXMin <= xVal && xVal <= stickXMax;
    boolean inStickZ = stickZMin <= zVal && zVal <= stickZMax;
    fill(255);
    noStroke();
    /*text(
      ""+stickXMin+" "+stickXMax+" "+stickZMin+" "+stickZMax,
      width*0.25+10, height*0.5+10
    );*/ 

    OscMessage posMsg = new OscMessage("/pos");
    posMsg.add(xVal);
    posMsg.add(zVal);
    oscP5.send(posMsg, oscDest);

    if(!(inStickX && inStickZ)) {
      col = round(gridSize*xVal - 0.5);
      row = round(gridSize*zVal - 0.5);
      
      OscMessage gridPosMsg = new OscMessage("/gridpos");
      gridPosMsg.add(col);
      gridPosMsg.add(row);
      oscP5.send(gridPosMsg, oscDest);
    }
  }
  
  String infoText = "";
  {
    int i = 0;
    for(Map.Entry<String, String> entry : paramNames.entrySet()) {
      if(i > 0) {
         infoText += "\n"; 
      }
      String addr = entry.getKey();
      String name = entry.getValue();
      infoText += name + " (" + addr + ") = " + params.get(name);
      i++;
    }
  }
      
  text(infoText, 10.0, height*0.5 + 10.0);

  maskViewG.beginDraw();
  maskViewG.shader(maskViewShader);
  maskViewShader.set("mask1", mask1);
  maskViewShader.set("mask2", mask2);
  maskViewG.rect(0, 0, kWidth, kHeight);
  maskViewG.endDraw();
  image(maskViewG, width*0.5, height*0.5, width*0.5, height*0.5);
  
  //image(detectG, width*0.5, height*0.5, width*0.5, height*0.5);
  
  float wExp = 1.0 + params.get("blobExpand");
  float hExp = wExp*height/width;
  
  noFill();
  rectMode(CENTER);
  strokeWeight(2);
  stroke(255, 0, 0);
  for(int i = 0; i < blobCount1; i++) {
    Blob b = blobs1[i];
    rect(
        b.x * width*0.5,
        b.y * height*0.5,
        b.w * wExp * width*0.5,
        b.h * hExp * height*0.5
    );
  }
  stroke(0, 0, 255);
  for(int i = 0; i < blobCount2; i++) {
    Blob b = blobs2[i];
    rect(
        b.x * width*0.5,
        b.y * height*0.5,
        b.w * wExp * width*0.5,
        b.h * hExp * height*0.5
    );
  } //<>//
  rectMode(CORNER);
  
  ellipseMode(CENTER);
  stroke(255, 255, 0);
  noFill();
  ellipse(
    x * width*0.5,
    y * height*0.5,
    10,
    10
  );
  
  float sqSize = 200.0;
  float sqMargin = 10.0;
  float circSize = 10.0;
  float sqX = width*0.5-sqSize-sqMargin;
  float sqY = height*0.5+sqMargin;
  if(0 <= col && 0 <= row) {
    noStroke();
    fill(64);
    float tileSize = sqSize/gridSize;
    float stickGrow = params.get("stickGrow");
    float kStickGrow = 1.0 + stickGrow;
    rect(
      sqX + tileSize*col - 0.5*tileSize*stickGrow,
      sqY + tileSize*row - 0.5*tileSize*stickGrow,
      tileSize*kStickGrow,
      tileSize*kStickGrow
    );
  }
  
  strokeWeight(1);
  stroke(128);
  noFill();
  for(int i = 1; i < gridSize; i++) {
    rect(sqX + sqSize*i/gridSize, sqY, 1, sqSize);
    rect(sqX, sqY + sqSize*i/gridSize, sqSize, 1);
  }
  
  stroke(255);
  rect(sqX, sqY, sqSize, sqSize);
  
  float circX = map(xLag.getValue(), 0.0, 1.0, sqX, sqX+sqSize);
  float circY = map(zLag.getValue(), 0.0, 1.0, sqY, sqY+sqSize);
  ellipse(circX, circY, circSize, circSize);

  noStroke();
  fill(255, 0, 255);
  float nearW = params.get("nearWidth");
  float nearDX = nearW * width*0.25;
  rect(width*0.25-nearDX, 0, 1, height*0.5);
  rect(width*0.25+nearDX, 0, 1, height*0.5);
  
  fill(0, 255, 255);
  float farW = params.get("farWidth");
  float farDX = farW * width*0.25;
  rect(width*0.25-farDX, 0, 1, height*0.5);
  rect(width*0.25+farDX, 0, 1, height*0.5);
  
  fill(255);
  String infoText2 = 
    "x = " + x +
    "\ny = " + y +
    "\nz = " + z +
    "\n" +
    "\nmx = " + mx +
    "\nmz = " + mz +
    "\nxLag = " + xLag.getValue() +
    "\nzLag = " + zLag.getValue() +
    "\ncol = " + col +
    "\nrow = " + row;

  text(infoText2, sqX, sqY+sqSize+sqMargin);
}

String removePrefix(String prefix, String text) {
   return text.startsWith(prefix) ? text.substring(prefix.length()) : null;
}

void oscEvent(OscMessage msg) {
  String addr = msg.addrPattern();

  if(paramNames.containsKey(addr)) {
    String name = paramNames.get(addr);
    params.put(name, msg.get(0).floatValue());
    return;
  }
  
  if(addr.equals("/3/push1") && msg.get(0).floatValue() > 0.0) {
    println("saving params");
    saveParams();
    return;
  }

  if(addr.equals("/3/push2") && msg.get(0).floatValue() > 0.0) {
    println("loading params");
    loadParams();
    return;
  }

  /* print the address pattern and the typetag of the received OscMessage */
  print("### received an osc message.");
  print(" addrpattern: "+msg.addrPattern());
  println(" typetag: "+msg.typetag());
}
