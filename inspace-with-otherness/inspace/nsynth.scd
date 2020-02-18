
s.boot;

~mon0 = Ndef(\mon0, { [SoundIn.ar(0), SoundIn.ar(1)] });
~mon0.play;

MIDIClient.init;
MIDIClient.destinations

~midio = MIDIOut.newByName("IAC Driver", "Bus 1");

~note0 = -6
~scales = [Scale.dorian];
~scales = [Scale.dorian, Scale.lydian, Scale.mixolydian];
~scales = [Scale.minor, Scale.dorian, Scale.major];
~amp = 0.3

(
~midip = Pdef(\midiPtn,
	Pbind(
		\type, \midi,
		\midiout, ~midio,
		\chan, 0,
		\scale, Pseq([1], inf).collect {
			~scales.choose;
		},
		\degree, Pwrand((0..6), [0.6, 0.4, 0.7, 0.4, 0.5, 0.4, 0.7].normalizeSum, inf).collect { |n|
			var oct = 0;
			n + ~note0 + (oct * 12);
		},
		\dur, Pfunc({
			exprand(0.1, 1.9)
		}),
		\amp, Pwhite(0.5, 1.0).collect{ |x| x * ~amp }
	)
);
)
~midip.play;
~midip.stop;
~midip.gui
~midip.dump
~midip.source.dump set(\scale, Prand([Scale.dorian], inf));
~midip.set(\scale, Prand([Scale.minor, Scale.dorian, Scale.major], inf));