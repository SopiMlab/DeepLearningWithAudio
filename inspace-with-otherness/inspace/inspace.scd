(
// 1. server config
s = Server.local;
/*s.options.device_("MOTU 828mk3 Hybrid");
s.options.numOutputBusChannels_(30);
s.options.sampleRate_(44100);*/

s.options.device_("Scarlett 18i20 USB");
s.options.numOutputBusChannels_(20);
s.options.sampleRate_(44100);

s.options.memSize_(2.pow(20));

// 2. initialize global variables
~out = 0;
~outs = [0,1,2,3,4,5];//[2,3,4,6,7,8];
~dir = thisProcess.nowExecutingPath.dirname;
~samplesDir = ~dir +/+ "samples";
~splitSamples = Set[
    "drone2"
];
~midiOutDeviceAndPort = nil;
//~midiOutDeviceAndPort = ["Scarlett 6i6 USB", "Scarlett 6i6 USB"];
//~midiOutDeviceAndPort = ["IAC Driver", "Bus 1"];
~oscPort = 12000;
~pdOscAddr = NetAddr("localhost", 12001);
~doServerBootCleanup = false; // `true` breaks Ndef!
~ctrlLag = 0.3;

~cleanup = {
    "cleanup".postln;

	s.newBusAllocators;
	if(~doServerBootCleanup) { ServerBoot.removeAll; };
	ServerTree.removeAll;
	ServerQuit.removeAll;
};

~cleanup.value;

~makeTxFunc = { |size, seed, n, mod|
    var randData0, tx;
    randData0 = thisThread.randData;
    thisThread.randSeed_(seed);

    tx = Env([-1.0, 1.0], [1.0]).discretize(size+1);
    tx = tx + (Signal.sineFill(size+1, n.collect { |i| rrand(0.0, 1.0) }, n.collect { |i| rrand(0.0, 2pi) }) * mod);
    tx = tx.normalize;

    thisThread.randData_(randData0);

    tx;
};

~satanMaximizer = { |in, envTime /* 0.001 to 0.0001 */, knee /* 0 to -90 dB */|
    DelayC.ar(in, 0.01, envTime * 0.5) * EnvFollow.ar(in, 1 - (envTime * SampleRate.ir).reciprocal).max(knee).reciprocal;
};

// 3. define piece-specific functions
~makeBuffers = {
    "makeBuffers".postln;

    b = Dictionary.new;
    PathName(~samplesDir).entries.do { |child1|
        case
        {child1.isFolder} {
            var items;
            items = List.new;
            child1.entries.do { |child2, i|
                if(child2.extension == "wav") {
                    items.add(Buffer.read(s, child2.fullPath, action: {
                        ("loaded "++child1.folderName++"/"++child2.fileName++" -> "++child1.folderName++"["++i++"]").postln;
                    }));
                }
            };
            b.add(child1.folderName.asSymbol -> items);
        }
        {child1.extension == "wav"} {
            if(~splitSamples.includes(child1.fileNameWithoutExtension), {
                var nChannels;
                nChannels = SoundFile.use(child1.fullPath, { |sf| sf.numChannels });
                b.add(
                    child1.fileNameWithoutExtension.asSymbol ->
                    nChannels.collect { |i|
                        Buffer.readChannel(s, child1.fullPath, channels: [i], action: {
                            ("loaded "++child1.fileName++", ch "++i++" -> "++child1.fileNameWithoutExtension++"["++i++"]").postln;
                        });
                    };
                );
            }, {
                b.add(
                    child1.fileNameWithoutExtension.asSymbol ->
                    Buffer.read(s, child1.fullPath, action: {
                        ("loaded "++child1.fileName++" -> "++child1.fileNameWithoutExtension).postln;
                    })
                );
            });
        }
        {true} {nil};
    };

    b.add(\percGrainEnv -> Buffer.sendCollection(s, Env([0.0, 1.0, 1.0, 0.0], [0.0, 0.1, 0.0], [\lin, \lin, 4.0]).discretize));

    //b.add(\shapeTx -> Buffer.sendCollection(s, ~makeTxFunc.value(1024, 41, 7, 0.4).asWavetableNoWrap));
    b.add(\shapeTx -> Buffer.sendCollection(s, ~makeTxFunc.value(1024, 129, 7, 0.7).asWavetableNoWrap));
};

~makeBusses = {
    "makeBusses".postln;

	~bus = Dictionary.new;

    ~bus.add(\drone1 -> Dictionary[
        \amp -> Bus.control(s, 1).set(0.0),
        \rateModDepth -> Bus.control(s, 1).set(0.0)
    ]);
    ~bus.add(\glitch -> Dictionary[
        \amp -> Bus.control(s, 1).set(0.0),
        \rate -> Bus.control(s, 1).set(0.0),
        \bend -> Bus.control(s, 1).set(0.0)
    ]);
    ~bus.add(\drone2 -> Dictionary[
        \amp -> Bus.control(s, 1).set(0.0)
    ]);
    ~bus.add(\percGrains -> Dictionary[
        \amp -> Bus.control(s, 1).set(0.0)
    ]);
    ~bus.add(\shape -> Dictionary[
        \amp -> Bus.control(s, 1).set(0.0)
    ]);

    ~bus.add(\percele -> Dictionary[
        \fx -> Bus.audio(s, ~outs.size),
        \amp -> Bus.control(s, 1).set(0.0)
    ]);

	//~bus.add(\reverb -> Bus.audio(s, 2));
};

~makeSynthDefs = {
	"makeSynthDefs".postln;

    SynthDef(\drone, { |out, freq, len, amp, cutoff = 1000.0|
        var imp, pos, rate0, rate, kRateMod, rateMod, rq, ampEnv, sig;
        imp = Impulse.ar(30.0);
        pos = TRand.ar(0.6, 0.9, imp);
        rate0 = 0.953;
        kRateMod = 1.0 + In.kr(~bus[\drone1][\rateModDepth]).lag(~ctrlLag);
        rateMod = TExpRand.ar(kRateMod.reciprocal, kRateMod, imp);
        rate = freq/48.midicps;
        sig = (0.1 * SinOsc.ar(0.5*freq))
        + GrainBuf.ar(1, imp, 0.3, b[\kcmhum_mono], rate * rateMod * rate0 * BufRateScale.kr(b[\kcmhum_mono]), pos);
        rq = 0.8;
        sig = RLPF.ar(sig, cutoff, rq, rq.sqrt.reciprocal);
        //ampEnv = EnvGen.ar(Env.perc(0.5*len, 0.5*len, curve: -4.0), doneAction: Done.freeSelf);
        ampEnv = EnvGen.ar(Env([0.0, 1.0, 0.0], [0.5*len, 0.5*len], [-4.0, -4.0]), doneAction: Done.freeSelf);
        sig = LeakDC.ar(sig) * amp * In.kr(~bus[\drone1][\amp]).lag(~ctrlLag) * ampEnv;
        Out.ar(out, sig);
    }).add;

    SynthDef(\sin, { |out, freq, len, amp, cutoff|
        Out.ar(out, SinOsc.ar(freq)*amp*0.3*EnvGen.ar(Env.perc(0.5*len, 0.5*len, -2), doneAction: Done.freeSelf));
    }).add;

    SynthDef(\machinery, { |out, amp|
        var impRate, imp, dur, rate, pos, sig;
        impRate = LFNoise0.ar(2.2).exprange(3.0, 6.0);
        imp = Impulse.ar(impRate);
        dur = impRate.reciprocal;//TRand.ar(0.2, 3.0, imp);
        rate = TExpRand.ar(0.5, 1.0, imp) * TWChoose.ar(imp, [DC.ar(1.0), DC.ar(1.0)], [4, 1].normalizeSum);
        pos = TRand.ar(0.1, 0.9, imp);
        sig = GrainBuf.ar(1, imp, dur, b[\emnoise_mono], rate * BufRateScale.kr(b[\emnoise_mono]), pos);
        sig = sig * amp;
        Out.ar(out, sig);
    }).add;

    SynthDef(\click, { |out, gate = 1.0, amp, rate = 0.1|
        var chain, sig;
        sig = Impulse.ar(rate);
        chain = FFT(LocalBuf(128), sig);
        chain = PV_MagShift(chain, Rand(0.2, 0.6), Rand(-25.0, -5.0));
        sig = IFFT(chain) * amp * EnvGen.ar(Env.asr(0.0, 1.0, 1.0), gate, doneAction: Done.freeSelf);
        Out.ar(out, sig);
    }).add;

    SynthDef(\silence, { |out, gate = 1.0|
        Out.ar(out, 0.0 * EnvGen.ar(Env.asr(0.0, 1.0, 0.0), gate, doneAction: Done.freeSelf));
    }).add;

    SynthDef(\glitch1, { |out, gate = 1.0, amp, bend = 0.0|
        var kPitch, freq, sig, chain;
        kPitch = bend.linexp(0.0, 1.0, 1.0, 0.5);
        freq = ExpRand(50.0, 400.0) * kPitch;
        sig = SinOsc.ar(freq*SinOsc.ar(Rand(3.0, 6.0)*freq, SinOsc.ar(Rand(2.0, 5.0)*freq)).range(0.1, 2.9));
        chain = FFT(LocalBuf(128), sig);
        chain = PV_BinScramble(chain, Rand(0.5, 1.0), Rand(0.2, 1.0), Impulse.ar(ExpRand(1.0, 20.0)));
        sig = IFFT(chain);
        sig = sig * amp * EnvGen.ar(Env.new([0,1,1,0], [0,ExpRand(0.03, 0.3),0]));
        EnvGen.ar(Env.asr(0.0, 1.0, 0.0), gate, doneAction: Done.freeSelf);
        Out.ar(out, sig);
    }).add;

    SynthDef(\glitch2, { |out, gate = 1.0, amp, bend = 0.0|
        var kPitch, freq0, freq1, freq, sig, chain;
        kPitch = bend.linexp(0.0, 1.0, 1.0, 0.5);
        freq0 = ExpRand(200.0, 1600.0) * kPitch;
        freq1 = ExpRand(30.0, 60.0) * kPitch;
        freq = EnvGen.ar(Env.new([freq0, freq1], [0.1], -16.0));
        sig = SinOscFB.ar(freq, ExpRand(0.5, 0.8));
        chain = FFT(LocalBuf(256), sig);
        chain = PV_BinScramble(chain, Rand(0.3, 0.6), ExpRand(0.001, 10.0));
        sig = IFFT(chain);
        sig = sig * amp * EnvGen.ar(Env.perc(0.0, 0.3));
        EnvGen.ar(Env.asr(0.0, 1.0, 0.0), gate, doneAction: Done.freeSelf);
        Out.ar(out, sig);
    }).add;

    SynthDef(\glitch3, { |out, gate = 1.0, amp, dur|
        var sig, chain;
        sig = Crackle.ar(Rand(1.4, 2.0));
        chain = FFT(LocalBuf(512), sig);
        chain = PV_BinShift(chain, Rand(0.3, 0.9), Rand(-200.0, 200.0));
        sig = IFFT(chain);
        sig = sig * amp * EnvGen.ar(Env.perc(dur, 0.01, curve: 3.0));
        EnvGen.ar(Env.asr(0.0, 1.0, 0.0), gate, doneAction: Done.freeSelf);
        Out.ar(out, sig);
    }).add;

    /*SynthDef(\drone2, { |freq, harm, rq, detune, riseDur, fallDur, amp, panRate, panPhase|
        var trig, rate, pos, sig, cutoff0, cutoff1, env, cutoff;
        trig = Impulse.ar(9.0);
        rate = freq / 48.midicps;
        pos = TRand.ar(0.1, 0.7, trig);
        sig = GrainBuf.ar(1, trig, 0.3, b[\drone2][0], rate * BufRateScale.kr(b[\drone2][0]), pos);
        cutoff0 = freq * harm / 2.0;
        cutoff1 = freq * harm;
        //cutoff = LFSaw.ar(envDur.reciprocal, -1.0).exprange(freq * harm * 0.5, freq * harm);
        env = EnvGen.ar(Env.new(
            [0.0, 0.0, 1.0, 0.0, 0.0],
            [0.0, riseDur, fallDur, 0.0],
            2.0, releaseNode: 3, loopNode: 1
        ));
        cutoff = env.exprange(cutoff0, cutoff1);
        sig = RLPF.ar(sig, cutoff, rq, rq.sqrt.reciprocal);
        sig = sig * env.exprange(-20.dbamp, 1.0) * amp + (FreeVerb.ar(CombN.ar(sig, 0.25, 0.25), 1.0, 0.5, 0.8) * 0.1);
        sig = PanAz.ar(~outs.size, sig, LFSaw.ar(panRate, panPhase), width: 2.2);
        sig = sig;

        ~outs.do { |out, i|
            Out.ar(out, sig[i]);
        }
    }).add;*/

    SynthDef(\drone2b, { |pos0, pos1, amp, cutoff = 1000.0, rq = 1.0, panRate, panPhase|
        var maxIx, start, end, dur, phase, sig;
        maxIx = BufFrames.kr(b[\drone2b]) - 1;
        start = pos0 * maxIx;
        end = pos1 * maxIx;
        dur = ((end - start) / SampleRate.ir).abs;
        phase = LFSaw.ar(dur.reciprocal, -1.0).range(start, end);
        sig = BufRd.ar(b[\drone2b].numChannels, b[\drone2b], phase);
        sig = RLPF.ar(sig, cutoff, rq, rq.sqrt.reciprocal);
        sig = sig * amp * In.kr(~bus[\drone2][\amp]).lag(~ctrlLag);
        sig = PanAz.ar(~outs.size, sig[0], LFSaw.ar(panRate, panPhase), width: 2.0);

        ~outs.do { |out, i|
            Out.ar(out, sig[i]);
        }
    }).add;

    /*SynthDef(\drone3, { |freq, harm, rq, detune, envDur, amp|
        var n, sig;
        n = 5;
        sig = n.collect { |i|
            var j, sig;
            j = i.linlin(0, n-1, -1.0, 1.0);
            sig = Saw.ar(freq * ((detune * j).midiratio));
            sig = sig / n;
            sig = Pan
            sig;
        }.sum;
        sig = RLPF.ar(sig, freq * harm, rq, rq.sqrt.reciprocal);
        sig = sig * amp;
        sig = PanAz.ar(~outs.size, sig, LFSaw.ar(0.15), width: 2.5);

        ~outs.do { |out, i|
            Out.ar(out, sig[i]);
        }
    }).add;*/

    SynthDef(\percGrains, { |amp, rateModDepth, envTime, knee, revAmp|
        var trigRate, trig, dur, pos, kRateMod, rate, pan, sig;
        trigRate = LFNoise2.ar(1.6).exprange(0.1, 0.4);
        trig = Impulse.ar(trigRate);
        dur = TRand.ar(0.4, 1.5);
        pos = TRand.ar(0.0, 1.0, trig);
        kRateMod = 1.0 + rateModDepth;
        rate = TExpRand.ar(kRateMod.reciprocal, kRateMod) * TChoose.ar(trig, [DC.ar(1.0), DC.ar(-1.0)]);
        pan = TRand.ar(-1.0, 1.0, trig);
        sig = GrainBuf.ar(
            numChannels: ~outs.size,
            trigger: trig,
            dur: dur,
            sndbuf: b[\continous1],
            rate: rate * BufRateScale.kr(b[\continous1]),
            pos: pos,
            pan: pan,
            envbufnum: b[\percGrainEnv]
        );
        //sig = ~satanMaximizer.value(sig, envTime, knee);
        sig = sig + (FreeVerb.ar(sig, 1.0, 0.9, 0.2) * revAmp);
        sig = LeakDC.ar(sig * amp * In.kr(~bus[\percGrains][\amp]).lag(~ctrlLag));
        ~outs.do { |out, i|
            Out.ar(out, sig[i]);
        };
    }).add;

    SynthDef(\shape, { |freq, rise, fall, curve, amp, pan, detune, drift, cutoff, rq, revAmp, revRoom, revDamp|
        var n, sig;
        n = 3;
        sig = n.collect { |i|
            var kDetune, kDrift, sig;
            kDetune = i.linlin(0, n-1, detune.neg, detune).midiratio;
            kDrift = LFNoise2.ar(7.6).range(drift.neg, drift).midiratio;
            sig = SinOsc.ar(freq * kDetune * kDrift);
            sig = Shaper.ar(b[\shapeTx], sig, LFNoise1.ar(1.6).exprange(0.4, 1.0));
            sig;
        }.sum / n;
        sig = sig * EnvGen.ar(Env([0.0, 1.0, 0.0], [rise, fall], curve: [curve, curve.neg]));
        sig = RLPF.ar(sig, cutoff, rq, rq.sqrt.reciprocal);
        sig = sig + (FreeVerb.ar(sig, 1.0, revRoom, revDamp) * revAmp);
        sig = LeakDC.ar(sig * amp * In.kr(~bus[\shape][\amp]).lag(~ctrlLag));
        sig = PanAz.ar(~outs.size, sig, pan);
        EnvGen.ar(Env([0.0, 0.0], [(rise+fall)+10.0]), doneAction: Done.freeSelf);
        ~outs.do { |out, i|
            Out.ar(out, sig[i]);
        }
    }).add;

    SynthDef(\percele, { |buf, rate, pan, amp, clip, pitchShift, spEnRatio, spEnStrength, send|
        var sig, chain;
        sig = PlayBuf.ar(buf.numChannels, buf, rate * BufRateScale.kr(buf), doneAction: Done.freeSelf);
        sig = Disintegrator.ar(sig, 0.4, -1.0);
        sig = sig.clip2(1.0 - clip) * (1.0 - clip).reciprocal;
        chain = FFT(LocalBuf(512), sig);
        chain = PV_PitchShift(chain, pitchShift);
        chain = PV_SpectralEnhance(chain, 8, spEnRatio, spEnStrength);
        sig = IFFT(chain);
        sig = sig * amp * In.kr(~bus[\percele][\amp]).lag(~ctrlLag);
        sig = PanAz.ar(~outs.size, sig, pan, width: 2.5);

        Out.ar(~bus[\percele][\fx], sig * send);
        ~outs.do { |out, i|
            Out.ar(out, sig[i]);
        };
    }).add;

    SynthDef(\perceleFx, {
        var sig;
        sig = In.ar(~bus[\percele][\fx], ~bus[\percele][\fx].numChannels);
        sig = FreeVerb.ar(sig, 1.0, 0.9, 0.3);

        ~outs.do { |out, i|
            Out.ar(out, sig[i]);
        };
    }).add;
};

~makeNodes = {
    "makeNodes".postln;

    //Ndef(\drone).play;

	//s.bind({

	//~mainGrp = Group.new;

    ~perceleFx = Synth(\perceleFx);

    /*~pianoSynth = Synth(\piano, [out: ~out, amp: 2.0, room: 1.0, damp: 0.5]);
    s.sync;
    ~piano = VSTPluginController(~pianoSynth, id: \piano);
    ~piano.open(~dir +/+ "VSUpright_v1_MacVST.vst", action: {
        "VSUpright loaded".postln;
    });*/



	//});
};

~makePatterns = {
    "makePatterns".postln;

    Pdef(\drone, Pbind(
        \instrument, \drone,
        \midinote, Pwrand([0, -2, 3, 7], [4, 3, 3, 1].normalizeSum, inf).collect { |n| (4*12)+n },
        \dur, Pwhite(0.5, 1.0, inf),
        \len, 5.0,
        \amp, 0.8,
        \cutoff, Pwhite(300.0, 1000.0),
        \out, Pxrand(~outs, inf)
    ));

    Pdef(\glitch,
        Ppar(
            ~outs.collect { |out|
                Pmul(
                    \amp, Pseq([0.7], inf).collect { |i| i * ~bus[\glitch][\amp].getSynchronous },
                    Pbindf(
                        Pwrand(
                            [
                                Pbind(
                                    \instrument, Pseq([\silence], 1),
                                    \amp, 0.0
                                ),
                                Pbind(
                                    \instrument, Pseq([\click], 1),
                                    \rate, 0.0,//Pexprand(1.4, 15.0, 1),
                                    \amp, 0.4
                                ),
                                Pbind(
                                    \instrument, Pseq([\glitch1], 1),
                                    \amp, 0.03
                                ),
                                Pbind(
                                    \instrument, Pseq([\glitch2], 1),
                                    \amp, 0.2
                                ),
                                Pbind(
                                    \instrument, Pseq([\glitch3], 1),
                                    \amp, 0.1
                                ),
                            ],
                            [2,2,4,1,2].normalizeSum,
                            inf,
                        ),
                        \bend, Pfunc { ~bus[\glitch][\bend].getSynchronous },
                        \dur, Pwhite(0.2, 1.0, inf).collect { |x| x * (~bus[\glitch][\rate].getSynchronous.linexp(0.0, 1.0, 1.0, 0.125)) },
                        \out, out
                    )
                )
            },
            1
        )
    );

    Pdef(\shape, Pbind(
        \instrument, \shape,
        \midinote, Pxrand([0,2,3,5,7,8,10], inf).collect { |n| 72+n + [-12].choose },
        \dur, Pwrand([Pexprand(2.0, 8.0, 1), Pexprand(0.001, 0.5, 1)], [5.0, 1.0].normalizeSum, inf),
        \rise, 3.0,
        \fall, 5.0,
        \curve, 1.0,
        \pan, Pwhite(-1.0, 1.0, inf),
        \detune, 0.12,
        \drift, 0.12,
        \cutoff, Pexprand(8000.0, 20000.0, inf),
        \rq, 0.9,
        \revAmp, 0.7,
        \revRoom, 0.9,
        \revDamp, 0.0,
        \amp, Pexprand(0.1, 0.3, inf)
    ));

    Pdef(\nsynth, Pbind(
        \instrument, \silence,
        \midinote, Pseq([0, 7, 12], inf).collect { |n|
            ~pdOscAddr.sendMsg("/pitch",48+n);
            n
        },
        \dur, 4.0
    ));

    Pdef(\percele, Pbind(
        \instrument, \percele,
        \buf, Pxrand(b[\perc], inf),
        \rate, Pexprand(0.5, 0.9, inf),
        \pan, Pwhite(-1.0, 1.0, inf),
        \dur, Pexprand(0.1, 2.0, inf),
        \amp, Pwhite(-6.0, 0.0).dbamp * 0.16,
        \clip, Pexprand(0.89, 0.97, inf),
        \pitchShift, Pexprand(0.5, 2.0, inf),
        \spEnRatio, Pexprand(1.0, 2.0, inf),
        \spEnStrength, Pexprand(0.1, 0.7, inf),
        \send, Pexprand(0.3, 0.4, inf)
    ));

    //~clock = TempoClock(120/60);
    //~midiFile = SimpleMIDIFile.read(~dir +/+ "test.mid");
};

~makeEvents = {
    "makeEvents".postln;

	e = Dictionary.new;

    e.add(\playDrone1 -> { Pdef(\drone).play; });
    e.add(\stopDrone1 -> { Pdef(\drone).stop; });

    e.add(\playGlitch -> { Pdef(\glitch).play; });
    e.add(\stopGlitch -> { Pdef(\glitch).stop; });

    /*e.add(\playDrone2 -> {
        if(~drone != nil) {
            e[\stopDrone2].value;
        };
        ~drone2 = {
            var harm, rq, riseDur, fallDur, amp, panRate;
            harm = 20;
            rq = 0.9;
            riseDur = 1.2;
            fallDur = 0.05;
            amp = 0.3;
            panRate = 0.3;
            [
                Synth(\drone2, [\freq: (36-0).midicps, \harm: harm, \rq: rq, \riseDur: riseDur*2.0, \fallDur: fallDur*2.0, \amp: amp, \panRate: panRate, \panPhase: 0.0]),
                Synth(\drone2, [\freq: (36+7).midicps, \harm: harm, \rq: rq, \riseDur: riseDur*0.8, \fallDur: fallDur*0.8, \amp: amp, \panRate: panRate, \panPhase: -1.0]);
            ]
        }.value;
    });
    e.add(\stopDrone2 -> {
        if(~drone2 != nil) {
            ~drone2.do { |s| s.free };
            ~drone2 = nil;
        }
    });*/

    e.add(\playDrone2b -> {
        if(~drone2b != nil) {
            e[\stopDrone2b].value;
        };
        ~drone2b = {
            var start, end1, end2, amp, cutoff, rq, panRate;
            start = 0.00;
            end1 = 0.3;
            end2 = (end1-start)*2.0/3.0+start;
            amp = 0.15;
            cutoff = 4000.0;
            rq = 0.6;
            panRate = 0.09;
            [
                Synth(\drone2b, [\pos1: start, \pos0: end1, \amp: amp, \cutoff: cutoff, \rq: rq, \panRate: panRate, \panPhase: 0.0]),
                Synth(\drone2b, [\pos0: start, \pos1: end2, \amp: amp, \cutoff: cutoff, \rq: rq, \panRate: panRate, \panPhase: 1.0]),
            ]
        }.value;
    });
    e.add(\stopDrone2b -> {
        if(~drone2b != nil) {
            ~drone2b.do { |s| s.free };
            ~drone2b = nil;
        }
    });

    e.add(\playPercGrains -> {
        if(~percGrains != nil) {
            e[\stopPercGrains].value;
        };
        ~percGrains = Synth(\percGrains, [\amp: 0.6, \rateModDepth: 0.5, \envTime: 0.001, \knee: -45.dbamp, \revAmp: 0.2])
    });
    e.add(\stopPercGrains -> {
        if(~percGrains != nil) {
            ~percGrains.free;
            ~percGrains = nil;
        }
    });

    e.add(\playShape -> { Pdef(\shape).play; });
    e.add(\stopShape -> { Pdef(\shape).stop; });

    e.add(\playPercele -> { Pdef(\percele).play; });
    e.add(\stopPercele -> { Pdef(\percele).stop; });

    e.add(\playComposition -> {
        ~seqClock = TempoClock.new(1.0).permanent_(true);
        ~segDur = 0.01;

        ~skip = 0.0;
        ~tCIn1 = 10.0; // crackle has faded in
        ~tFIn0 = ~tCIn1 + 20.0; // fridge starts fading in
        ~tFIn1 = ~tFIn0 + 30.0; // fridge has faded in
        ~tSIn0 = ~tFIn1 + 20.0; // synth starts fading in
        ~tSIn1 = ~tSIn0 + 30.0; // synth has faded in
        ~tCRIn0 = ~tSIn1 + 20.0; // fridge/synth start fading out, crackle rate starts to increase
        ~tCRIn1 = ~tCRIn0 + 30.0; // fridge/synth have faded out, crackle rate has increased
        ~tPIn0 = ~tCRIn0 + 15.0; // percussion starts fading in
        ~tPIn1 = ~tPIn0 + 30.0; // percussion has faded in
        ~tCROut0 = ~tPIn1 + 30.0; // crackle rate starts to decrease
        ~tCROut1 = ~tCROut0 + 15.0; // crackle rate has decreased
        ~tGIn0 = ~tCROut0 + 10.0; // grains start fading in
        ~tGIn1 = ~tGIn0 + 15.0; // grains have faded in
        ~tPOut0 = ~tGIn1 + 15.0; // percussion starts fading out
        ~tPOut1 = ~tPOut0 + 15.0; // percussion has faded out
        ~tGOut0 = ~tPOut1 + 15.0; // grains start fading out
        ~tGOut1 = ~tGOut0 + 15.0; // grains have faded out
        ~tCOut0 = ~tGOut1 + 0.0; // crackle starts fading out
        ~tCOut1 = ~tCOut0 + 15.0; // crackle has faded out

        e[\stopGlitch].value;
        e[\playGlitch].value;
        e[\stopDrone1].value;
        e[\playDrone1].value;
        e[\stopDrone2b].value;
        e[\playDrone2b].value;
        e[\stopPercele].value;
        e[\playPercele].value;
        e[\stopPercGrains].value;
        e[\playPercGrains].value;

        Pdef(\composition, Ppar(
            [
                // crackle amp
                Pbind(
                    \type, \rest,
                    \value, Pseg(
                        Pseq([0.0, 1.0, 1.0, 0.0, 0.0]),
                        Pseq([~tCIn1, ~tCOut0-~tCIn1, ~tCOut1-~tCOut0, 4.0].collect { |d| (d-~skip).max(0.0) }),
                        [4.0, 0.0, -4.0, 0.0]
                    ),
                    \dur, ~segDur
                ).collect { |e|
                    ~bus[\glitch][\amp].set(e[\value]);
                    e
                },

                // crackle rate
                Pbind(
                    \type, \rest,
                    \value, Pseg(
                        Pseq([0.0, 0.0, 1.0, 1.0, 0.0, 0.0]),
                        Pseq([~tCRIn0, ~tCRIn1-~tCRIn0, ~tCROut0-~tCRIn1, ~tCROut1-~tCROut0, 1.0].collect { |d| (d-~skip).max(0.0) }),
                        0.0
                    ),
                    \dur, ~segDur
                ).collect { |e|
                    ~bus[\glitch][\rate].set(e[\value]);
                    e
                },

                // fridge amp
                Pbind(
                    \type, \rest,
                    \value, Pseg(
                        Pseq([0.0, 0.0, 1.0, 1.0, 0.0, 0.0]),
                        Pseq([~tFIn0, ~tFIn1-~tFIn0, ~tCRIn0-~tFIn1, ~tCRIn1-~tCRIn0, 1.0].collect { |d| (d-~skip).max(0.0) }),
                        [0.0, 8.0, 0.0, -8.0, 0.0]
                    ),
                    \dur, ~segDur
                ).collect { |e|
                    ~bus[\drone1][\amp].set(e[\value]);
                    e
                },

                // synth amp
                Pbind(
                    \type, \rest,
                    \value, Pseg(
                        Pseq([0.0, 0.0, 1.0, 1.0, 0.0, 0.0]),
                        Pseq([~tSIn0, ~tSIn1-~tSIn0, ~tCRIn0-~tSIn1, ~tCRIn1-~tCRIn0, 1.0].collect { |d| (d-~skip).max(0.0) }),
                        [0.0, 4.0, 0.0, -4.0, 0.0]
                    ),
                    \dur, ~segDur
                ).collect { |e|
                    ~bus[\drone2][\amp].set(e[\value]);
                    e
                },

                // perc amp
                Pbind(
                    \type, \rest,
                    \value, Pseg(
                        Pseq([0.0, 0.0, 1.0, 1.0, 0.0, 0.0]),
                        Pseq([~tPIn0, ~tPIn1-~tPIn0, ~tPOut0-~tPIn1, ~tPOut1-~tPOut0, 1.0].collect { |d| (d-~skip).max(0.0) }),
                        [0.0, 4.0, 0.0, -4.0, 0.0]
                    ),
                    \dur, ~segDur
                ).collect { |e|
                    ~bus[\percele][\amp].set(e[\value]);
                    e
                },

                // grains amp
                Pbind(
                    \type, \rest,
                    \value, Pseg(
                        Pseq([0.0, 0.0, 1.0, 1.0, 0.0, 0.0]),
                        Pseq([~tGIn0, ~tGIn1-~tGIn0, ~tGOut0-~tGIn1, ~tGOut1-~tGOut0, 1.0].collect { |d| (d-~skip).max(0.0) }),
                        [0.0, 2.0, 0.0, -2.0, 0.0]
                    ),
                    \dur, ~segDur
                ).collect { |e|
                    ~bus[\percGrains][\amp].set(e[\value]);
                    e
                },

                Pbind(
                    \type, \rest,
                    \notes, Pseq([
                        [
                            0, -5, -9, -7, -4, -2, 2, 3,
                            0, 3, 2, -4, -7, -9, -5, -4
                        ] + 60,
                        [
                            0, -2, 0, 3, -5, -9, -7, -3
                        ] + 60,
                        [
                            7, 12, 10, 5, 9, 10,
                            7, 12, 15, 14, 10, 5,
                            0, 7, 3, 2, -2, -3,
                            0, 7, 10, 9, 5, 3
                        ] + 60,
                        [
                            0, -5, -9, -7, -4, -2, 2, 3,
                            0, 3, 2, -4, -7, -9, -5, -4
                        ] + 60
                    ]),
                    \dur, Pseq([~tSIn0, ~tSIn1-~tSIn0, ~tCRIn0-~tSIn1, 0.1])
                ).collect { |e|
                    ~pdOscAddr.sendMsg("/notes", *e[\notes]);
                    e
                }
            ],
            inf
        )).play(~seqClock);
    });
};

~makeControls = {
    "makeControls".postln;

    OSCdef.newMatching(\toggleDrone1, { |msg|
	    var on = msg[1];
        if(on != 0.0, {
            e[\playDrone1].value;
        }, {
            e[\stopDrone1].value;
        });
    },  "/1/toggle1", recvPort: ~oscPort);
    OSCdef.newMatching(\drone1Amp, { |msg|
        var value = msg[1];
        ~bus[\drone1][\amp].set(value);
    },  "/1/fader1", recvPort: ~oscPort);
    MIDIdef.cc(\drone1Amp, { |val, num|
        val.postln;
    }, 20, 0);
    OSCdef.newMatching(\drone1RateModDepth, { |msg|
        var value = msg[1].lincurve(0.0, 1.0, 0.0, 1.0, 8.0);
        ~bus[\drone1][\rateModDepth].set(value);
    },  "/1/fader2", recvPort: ~oscPort);

    OSCdef.newMatching(\toggleGlitch, { |msg|
	    var on = msg[1];
        if(on != 0.0, {
            e[\playGlitch].value;
        }, {
            e[\stopGlitch].value;
        });
    },  "/1/toggle2", recvPort: ~oscPort);
    OSCdef.newMatching(\glitchAmp, { |msg|
        var value = msg[1];
        ~bus[\glitch][\amp].set(value);
    },  "/1/fader4", recvPort: ~oscPort);
    OSCdef.newMatching(\glitchRate, { |msg|
        var value = msg[1];
        ~bus[\glitch][\rate].set(value);
    },  "/1/fader5", recvPort: ~oscPort);
    OSCdef.newMatching(\glitchBend, { |msg|
        var value = msg[1];
        ~bus[\glitch][\bend].set(value);
    },  "/1/fader6", recvPort: ~oscPort);

    OSCdef.newMatching(\toggleDrone2, { |msg|
	    var on = msg[1];
        if(on != 0.0, {
            e[\playDrone2b].value;
        }, {
            e[\stopDrone2b].value;
        });
    },  "/1/toggle3", recvPort: ~oscPort);
    OSCdef.newMatching(\drone2Amp, { |msg|
        var value = msg[1];
        ~bus[\drone2][\amp].set(value);
    },  "/1/fader7", recvPort: ~oscPort);

    OSCdef.newMatching(\togglePercGrains, { |msg|
	    var on = msg[1];
        if(on != 0.0, {
            e[\playPercGrains].value;
        }, {
            e[\stopPercGrains].value;
        });
    },  "/1/toggle4", recvPort: ~oscPort);
    OSCdef.newMatching(\percGrainsAmp, { |msg|
        var value = msg[1];
        ~bus[\percGrains][\amp].set(value);
    },  "/1/fader10", recvPort: ~oscPort);

    OSCdef.newMatching(\togglePercele, { |msg|
	    var on = msg[1];
        if(on != 0.0, {
            e[\playPercele].value;
        }, {
            e[\stopPercele].value;
        });
    },  "/1/toggle5", recvPort: ~oscPort);
    OSCdef.newMatching(\perceleAmp, { |msg|
        var value = msg[1];
        ~bus[\percele][\amp].set(value);
    },  "/1/fader13", recvPort: ~oscPort);

	/*MIDIdef.cc(\testMidi, { |val, num|
	    "testMidi: val = ".post; val.post; ", num = ".post; num.postln;
	});*/
};

// 4. register functions with ServerBoot/Quit/Tree
ServerBoot.add { s.bind { ~makeBuffers.value; s.sync } };
ServerBoot.add { s.bind { ~makeBusses.value; s.sync } };
ServerQuit.add(~cleanup);

// 5. boot server
s.waitForBoot {
    "boot".postln;

    MIDIIn.connectAll;

    if(~midiOutDeviceAndPort != nil) {
        "use midi".postln;
        ~midiOut = MIDIOut.newByName(~midiOutDeviceAndPort[0], ~midiOutDeviceAndPort[1]);
        s.sync;
    } {
        "don't use midi".postln;
    };

    s.bind {
        ~makeSynthDefs.value;

        s.sync;
    };

    ServerTree.add { s.bind { ~makeNodes.value; s.sync } };
    ServerTree.add { s.bind { ~makePatterns.value; s.sync } };
    ServerTree.add { s.bind { ~makeEvents.value; s.sync } };
    ServerTree.add { s.bind { ~makeControls.value; s.sync } };
    ServerTree.add {
        "playing composition".postln;
        e[\playComposition].value;
    };
    s.freeAll;

    s.sync;

    "boot finished".postln;
};
)
