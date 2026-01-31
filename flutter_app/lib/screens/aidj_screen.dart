import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:just_audio/just_audio.dart';
import '../styles.dart';

class AiDjScreen extends StatefulWidget {
  const AiDjScreen({super.key});
  @override
  State<AiDjScreen> createState() => _AiDjScreenState();
}

class _AiDjScreenState extends State<AiDjScreen> with TickerProviderStateMixin {
  final AudioPlayer _playerA = AudioPlayer();
  final AudioPlayer _playerB = AudioPlayer();
  String? _trackAName;
  String? _trackBName;
  double _crossfader = 0.5;
  bool _isAutoMixing = false;
  late AnimationController _autoMixController;

  @override
  void initState() {
    super.initState();
    _autoMixController =
        AnimationController(vsync: this, duration: const Duration(seconds: 3));
    _autoMixController.addListener(() {
      if (_isAutoMixing) {
        setState(() => _crossfader = _autoMixController.value);
        _playerA.setVolume(1 - _crossfader);
        _playerB.setVolume(_crossfader);
      }
    });
  }

  @override
  void dispose() {
    _playerA.dispose();
    _playerB.dispose();
    _autoMixController.dispose();
    super.dispose();
  }

  Future<void> _loadTrack(String deck) async {
    try {
      final result = await FilePicker.platform.pickFiles(type: FileType.audio);
      if (result != null && result.files.single.path != null) {
        final path = result.files.single.path!;
        final name = result.files.single.name;
        if (deck == 'A') {
          await _playerA.setFilePath(path);
          setState(() => _trackAName = name);
        } else {
          await _playerB.setFilePath(path);
          setState(() => _trackBName = name);
        }
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text('Loaded: $name'),
            backgroundColor: AppTheme.successGreen));
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red));
    }
  }

  void _togglePlayA() {
    if (_playerA.playing) {
      _playerA.pause();
    } else {
      _playerA.play();
    }
    setState(() {});
  }

  void _togglePlayB() {
    if (_playerB.playing) {
      _playerB.pause();
    } else {
      _playerB.play();
    }
    setState(() {});
  }

  void _autoMix() {
    setState(() => _isAutoMixing = true);
    if (!_playerA.playing) _playerA.play();
    _autoMixController.forward(from: 0).then((_) {
      if (!_playerB.playing) _playerB.play();
      setState(() => _isAutoMixing = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: AppTheme.gradientBackground(AppTheme.aiDjGradient),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          title: const Text('🎧 AI DJ Studio',
              style: TextStyle(color: Colors.white)),
          iconTheme: const IconThemeData(color: Colors.white),
        ),
        body: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              const Text('Smart mixing with AI-powered transitions',
                  style: TextStyle(color: Color(0xFF00D4FF), fontSize: 14)),
              const SizedBox(height: 24),
              // Deck A
              _buildDeck('A', _trackAName, _playerA.playing, _togglePlayA,
                  () => _loadTrack('A')),
              const SizedBox(height: 24),
              // Crossfader
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(16)),
                child: Column(
                  children: [
                    const Text('AI Crossfader',
                        style: TextStyle(color: Colors.white70)),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        const Text('A', style: TextStyle(color: Colors.white)),
                        Expanded(
                          child: Slider(
                            value: _crossfader,
                            onChanged: (v) {
                              setState(() => _crossfader = v);
                              _playerA.setVolume(1 - v);
                              _playerB.setVolume(v);
                            },
                            activeColor: const Color(0xFF00D4FF),
                          ),
                        ),
                        const Text('B', style: TextStyle(color: Colors.white)),
                      ],
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton.icon(
                      onPressed: _isAutoMixing ? null : _autoMix,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF00D4FF),
                        foregroundColor: Colors.black,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 32, vertical: 16),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(30)),
                      ),
                      icon: Icon(_isAutoMixing
                          ? Icons.hourglass_empty
                          : Icons.auto_awesome),
                      label: Text(_isAutoMixing ? 'Mixing...' : '🤖 Auto Mix'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              // Deck B
              _buildDeck('B', _trackBName, _playerB.playing, _togglePlayB,
                  () => _loadTrack('B')),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDeck(String label, String? trackName, bool isPlaying,
      VoidCallback onPlayPause, VoidCallback onLoad) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: AppTheme.turntableDeck,
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Deck $label',
                  style: const TextStyle(
                      color: Color(0xFF00D4FF),
                      fontSize: 20,
                      fontWeight: FontWeight.bold)),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                    color:
                        trackName != null ? AppTheme.successGreen : Colors.grey,
                    borderRadius: BorderRadius.circular(20)),
                child: Text(trackName != null ? 'Ready' : 'Empty',
                    style: const TextStyle(color: Colors.white, fontSize: 12)),
              ),
            ],
          ),
          const SizedBox(height: 16),
          // Turntable visual
          Container(
            width: 120,
            height: 120,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: const Color(0xFF0A0A15),
              border: Border.all(color: const Color(0xFF00D4FF), width: 2),
              boxShadow: [
                BoxShadow(
                    color: const Color(0xFF00D4FF).withOpacity(0.3),
                    blurRadius: 20,
                    spreadRadius: 2)
              ],
            ),
            child: Center(
              child: Container(
                width: 30,
                height: 30,
                decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: trackName != null && isPlaying
                        ? const Color(0xFF00D4FF)
                        : Colors.grey),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text(trackName ?? 'No track loaded',
              style: TextStyle(
                  color: trackName != null ? Colors.white : Colors.white54),
              textAlign: TextAlign.center,
              overflow: TextOverflow.ellipsis),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              ElevatedButton.icon(
                  onPressed: onLoad,
                  style:
                      ElevatedButton.styleFrom(backgroundColor: Colors.white24),
                  icon: const Icon(Icons.upload, color: Colors.white),
                  label: const Text('Upload',
                      style: TextStyle(color: Colors.white))),
              const SizedBox(width: 12),
              ElevatedButton.icon(
                onPressed: trackName != null ? onPlayPause : null,
                style: ElevatedButton.styleFrom(
                    backgroundColor:
                        isPlaying ? Colors.orange : AppTheme.successGreen),
                icon: Icon(isPlaying ? Icons.pause : Icons.play_arrow,
                    color: Colors.white),
                label: Text(isPlaying ? 'Pause' : 'Play',
                    style: const TextStyle(color: Colors.white)),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
