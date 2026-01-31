import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../styles.dart';
import '../config.dart';

class JukeboxScreen extends StatefulWidget {
  const JukeboxScreen({super.key});
  @override
  State<JukeboxScreen> createState() => _JukeboxScreenState();
}

class _JukeboxScreenState extends State<JukeboxScreen> {
  int _currentView = 0; // 0=menu, 1=host, 2=guest
  String? sessionId;
  String? role;
  String? qrCode;
  WebSocketChannel? channel;
  List<dynamic> queue = [];
  List<dynamic> playedSongs = [];
  double totalTips = 0;

  final hostPartyNameCtrl = TextEditingController();
  final hostNameCtrl = TextEditingController();
  final hostPasswordCtrl = TextEditingController();
  final joinCodeCtrl = TextEditingController();
  final joinNameCtrl = TextEditingController();
  final joinPasswordCtrl = TextEditingController();
  final resumeCodeCtrl = TextEditingController();
  final resumePasswordCtrl = TextEditingController();
  final songNameCtrl = TextEditingController();
  final songArtistCtrl = TextEditingController();
  final tipCtrl = TextEditingController();

  @override
  void dispose() {
    channel?.sink.close();
    hostPartyNameCtrl.dispose();
    hostNameCtrl.dispose();
    hostPasswordCtrl.dispose();
    joinCodeCtrl.dispose();
    joinNameCtrl.dispose();
    joinPasswordCtrl.dispose();
    resumeCodeCtrl.dispose();
    resumePasswordCtrl.dispose();
    songNameCtrl.dispose();
    songArtistCtrl.dispose();
    tipCtrl.dispose();
    super.dispose();
  }

  void _showError(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: Colors.red),
    );
  }

  void _showSuccess(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: AppTheme.successGreen),
    );
  }

  Future<void> _createSession() async {
    try {
      final res = await http.post(
        EnvConfig.api('/api/sessions/create'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'name': hostPartyNameCtrl.text,
          'artist_id': hostNameCtrl.text,
          'password': hostPasswordCtrl.text,
        }),
      );
      if (res.statusCode >= 200 && res.statusCode < 300) {
        final data = jsonDecode(res.body);
        setState(() {
          sessionId = data['session_id']?.toString();
          qrCode = data['qr_code']?.toString();
          role = 'host';
          _currentView = 1;
        });
        _connectWs();
        await _refreshQueue();
        _showSuccess('Jukebox created! Code: $sessionId');
      } else {
        _showError('Failed to create session');
      }
    } catch (e) {
      _showError('Error: $e');
    }
  }

  Future<void> _joinSession() async {
    final code = joinCodeCtrl.text.trim().toUpperCase();
    try {
      final res = await http.post(
        EnvConfig.api('/api/sessions/$code/join'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'guest_name': joinNameCtrl.text,
          'password': joinPasswordCtrl.text,
        }),
      );
      if (res.statusCode >= 200 && res.statusCode < 300) {
        setState(() {
          sessionId = code;
          role = 'guest';
          _currentView = 2;
        });
        _connectWs();
        await _refreshQueue();
        _showSuccess('Joined jukebox!');
      } else {
        _showError('Invalid code or password');
      }
    } catch (e) {
      _showError('Error: $e');
    }
  }

  Future<void> _resumeSession() async {
    final code = resumeCodeCtrl.text.trim().toUpperCase();
    try {
      final res = await http.post(
        EnvConfig.api('/api/sessions/$code/resume'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'password': resumePasswordCtrl.text}),
      );
      if (res.statusCode >= 200 && res.statusCode < 300) {
        final data = jsonDecode(res.body);
        setState(() {
          sessionId = code;
          qrCode = data['qr_code']?.toString();
          role = 'host';
          _currentView = 1;
        });
        _connectWs();
        await _refreshQueue();
        _showSuccess('Session resumed!');
      } else {
        _showError('Invalid code or password');
      }
    } catch (e) {
      _showError('Error: $e');
    }
  }

  void _connectWs() {
    if (sessionId == null) return;
    channel?.sink.close();
    channel = WebSocketChannel.connect(EnvConfig.ws('/ws/$sessionId'));
    channel!.stream.listen((event) {
      try {
        final data = jsonDecode(event as String);
        if ([
          'new_request',
          'request_completed',
          'request_skipped',
          'queue_update'
        ].contains(data['type'])) {
          _refreshQueue();
        }
      } catch (_) {}
    });
  }

  Future<void> _refreshQueue() async {
    if (sessionId == null) return;
    try {
      final res = await http.get(EnvConfig.api('/api/requests/$sessionId'));
      if (res.statusCode >= 200 && res.statusCode < 300) {
        final data = jsonDecode(res.body) as List<dynamic>;
        setState(() {
          queue = data.where((r) => r['status'] == 'queued').toList();
          playedSongs = data.where((r) => r['status'] == 'completed').toList();
          totalTips =
              data.fold(0.0, (sum, r) => sum + (r['tip_amount'] ?? 0.0));
        });
      }
    } catch (e) {
      _showError('Error refreshing: $e');
    }
  }

  Future<void> _submitRequest() async {
    if (sessionId == null) return;
    final tip = double.tryParse(tipCtrl.text) ?? 0.0;
    try {
      final res = await http.post(
        EnvConfig.api('/api/requests/submit'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'song_name': songNameCtrl.text,
          'artist': songArtistCtrl.text,
          'requester_name':
              role == 'host' ? hostNameCtrl.text : joinNameCtrl.text,
          'session_id': sessionId,
          'tip_amount': tip,
        }),
      );
      if (res.statusCode >= 200 && res.statusCode < 300) {
        songNameCtrl.clear();
        songArtistCtrl.clear();
        tipCtrl.clear();
        Navigator.pop(context);
        await _refreshQueue();
        _showSuccess('Song requested!');
      }
    } catch (e) {
      _showError('Error: $e');
    }
  }

  Future<void> _completeRequest(String id) async {
    final uri = EnvConfig.api('/api/requests/$id/complete')
        .replace(queryParameters: {'session_id': sessionId!});
    await http.post(uri);
    await _refreshQueue();
  }

  Future<void> _skipRequest(String id) async {
    final uri = EnvConfig.api('/api/requests/$id/skip')
        .replace(queryParameters: {'session_id': sessionId!});
    await http.post(uri);
    await _refreshQueue();
  }

  void _showRequestDialog() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        padding: EdgeInsets.only(
            bottom: MediaQuery.of(ctx).viewInsets.bottom,
            top: 24,
            left: 24,
            right: 24),
        decoration: const BoxDecoration(
          color: Color(0xFF1A1A2E),
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('🎵 Request a Song',
                style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: Colors.white)),
            const SizedBox(height: 16),
            TextField(
                controller: songNameCtrl,
                style: const TextStyle(color: Colors.black),
                decoration: AppTheme.inputDecoration('Song Name',
                    prefixIcon: Icons.music_note)),
            const SizedBox(height: 12),
            TextField(
                controller: songArtistCtrl,
                style: const TextStyle(color: Colors.black),
                decoration: AppTheme.inputDecoration('Artist',
                    prefixIcon: Icons.person)),
            const SizedBox(height: 12),
            TextField(
                controller: tipCtrl,
                style: const TextStyle(color: Colors.black),
                keyboardType: TextInputType.number,
                decoration: AppTheme.inputDecoration('Tip Amount (₹)',
                    prefixIcon: Icons.attach_money)),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                  color: Colors.white10,
                  borderRadius: BorderRadius.circular(12)),
              child: const Column(
                children: [
                  Text('💡 Tip ₹10+ for VIP Queue!',
                      style: TextStyle(
                          color: Colors.amber, fontWeight: FontWeight.bold)),
                  SizedBox(height: 4),
                  Text('VIP songs play before regular requests',
                      style: TextStyle(color: Colors.white70, fontSize: 12)),
                ],
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
                onPressed: _submitRequest,
                style: AppTheme.primaryButton,
                child: const Text('Submit Request')),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: AppTheme.gradientBackground(AppTheme.jukeboxGradient),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          title:
              const Text('🎵 Jukebox', style: TextStyle(color: Colors.white)),
          iconTheme: const IconThemeData(color: Colors.white),
        ),
        body: _currentView == 0
            ? _buildMenu()
            : (_currentView == 1 ? _buildHostDashboard() : _buildGuestView()),
      ),
    );
  }

  Widget _buildMenu() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          _buildCard('🎤 Host a Jukebox', [
            TextField(
                controller: hostPartyNameCtrl,
                style: const TextStyle(color: Colors.black),
                decoration: AppTheme.inputDecoration('Party Name')),
            const SizedBox(height: 12),
            TextField(
                controller: hostNameCtrl,
                style: const TextStyle(color: Colors.black),
                decoration: AppTheme.inputDecoration('Your Name')),
            const SizedBox(height: 12),
            TextField(
                controller: hostPasswordCtrl,
                obscureText: true,
                style: const TextStyle(color: Colors.black),
                decoration: AppTheme.inputDecoration('Password')),
            const SizedBox(height: 16),
            ElevatedButton(
                onPressed: _createSession,
                style: AppTheme.primaryButton,
                child: const Text('Create Jukebox')),
          ]),
          const SizedBox(height: 20),
          _buildCard('🎉 Join Jukebox', [
            TextField(
                controller: joinCodeCtrl,
                style: const TextStyle(color: Colors.black),
                decoration: AppTheme.inputDecoration('Session Code')),
            const SizedBox(height: 12),
            TextField(
                controller: joinNameCtrl,
                style: const TextStyle(color: Colors.black),
                decoration: AppTheme.inputDecoration('Your Name')),
            const SizedBox(height: 12),
            TextField(
                controller: joinPasswordCtrl,
                obscureText: true,
                style: const TextStyle(color: Colors.black),
                decoration: AppTheme.inputDecoration('Password')),
            const SizedBox(height: 16),
            ElevatedButton(
                onPressed: _joinSession,
                style: AppTheme.secondaryButton,
                child: const Text('Join')),
          ]),
          const SizedBox(height: 20),
          _buildCard('🔄 Resume Session', [
            TextField(
                controller: resumeCodeCtrl,
                style: const TextStyle(color: Colors.black),
                decoration: AppTheme.inputDecoration('Session Code')),
            const SizedBox(height: 12),
            TextField(
                controller: resumePasswordCtrl,
                obscureText: true,
                style: const TextStyle(color: Colors.black),
                decoration: AppTheme.inputDecoration('Password')),
            const SizedBox(height: 16),
            OutlinedButton(
                onPressed: _resumeSession,
                style: AppTheme.tertiaryButton,
                child: const Text('Resume')),
          ]),
        ],
      ),
    );
  }

  Widget _buildCard(String title, List<Widget> children) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.1),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white24)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text(title,
            style: const TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.bold)),
        const SizedBox(height: 16),
        ...children
      ]),
    );
  }

  Widget _buildHostDashboard() {
    final vipSongs = queue.where((r) => (r['tip_amount'] ?? 0) >= 10).toList();
    final regularSongs =
        queue.where((r) => (r['tip_amount'] ?? 0) < 10).toList();

    return Column(
      children: [
        // Stats Row
        Padding(
          padding: const EdgeInsets.all(16),
          child: Row(children: [
            Expanded(
                child: AppTheme.statsCardWidget(
                    value: '${queue.length}', label: 'In Queue')),
            const SizedBox(width: 12),
            Expanded(
                child: AppTheme.statsCardWidget(
                    value: '${playedSongs.length}', label: 'Played')),
            const SizedBox(width: 12),
            Expanded(
                child: AppTheme.statsCardWidget(
                    value: '₹${totalTips.toStringAsFixed(0)}',
                    label: 'Tips',
                    valueColor: AppTheme.vipGold)),
          ]),
        ),
        // QR Code + Session Code
        if (qrCode != null)
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
                color: Colors.white, borderRadius: BorderRadius.circular(16)),
            child: Row(children: [
              QrImageView(
                  data: 'http://localhost:5000/join/$sessionId', size: 80),
              const SizedBox(width: 16),
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('Session Code',
                    style: TextStyle(color: Colors.grey)),
                Text(sessionId ?? '',
                    style: const TextStyle(
                        fontSize: 28, fontWeight: FontWeight.bold)),
              ]),
            ]),
          ),
        const SizedBox(height: 12),
        // Queue
        Expanded(
          child: RefreshIndicator(
            onRefresh: _refreshQueue,
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: [
                if (vipSongs.isNotEmpty) ...[
                  const Text('👑 VIP Queue',
                      style: TextStyle(
                          color: Colors.amber,
                          fontSize: 16,
                          fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  ...vipSongs.map((r) => AppTheme.songCard(
                        songName: r['song_name'] ?? '',
                        artist: r['artist'] ?? '',
                        requester: r['requester_name'] ?? '',
                        tipAmount: (r['tip_amount'] ?? 0).toDouble(),
                        status: r['status'] ?? '',
                        isHost: true,
                        onComplete: () => _completeRequest(r['id'].toString()),
                        onSkip: () => _skipRequest(r['id'].toString()),
                      )),
                  const SizedBox(height: 16),
                ],
                if (regularSongs.isNotEmpty) ...[
                  const Text('🎵 Regular Queue',
                      style: TextStyle(
                          color: Colors.white70,
                          fontSize: 16,
                          fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  ...regularSongs.map((r) => AppTheme.songCard(
                        songName: r['song_name'] ?? '',
                        artist: r['artist'] ?? '',
                        requester: r['requester_name'] ?? '',
                        tipAmount: (r['tip_amount'] ?? 0).toDouble(),
                        status: r['status'] ?? '',
                        isHost: true,
                        onComplete: () => _completeRequest(r['id'].toString()),
                        onSkip: () => _skipRequest(r['id'].toString()),
                      )),
                ],
                if (queue.isEmpty)
                  const Center(
                      child: Padding(
                          padding: EdgeInsets.all(40),
                          child: Text('No songs in queue',
                              style: TextStyle(color: Colors.white54)))),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildGuestView() {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: ElevatedButton.icon(
            onPressed: _showRequestDialog,
            style: AppTheme.primaryButton,
            icon: const Icon(Icons.add),
            label: const Text('Request a Song'),
          ),
        ),
        const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Text('🎵 Up Next',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.bold))),
        Expanded(
          child: RefreshIndicator(
            onRefresh: _refreshQueue,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: queue
                  .map((r) => AppTheme.songCard(
                        songName: r['song_name'] ?? '',
                        artist: r['artist'] ?? '',
                        requester: r['requester_name'] ?? '',
                        tipAmount: (r['tip_amount'] ?? 0).toDouble(),
                        status: r['status'] ?? '',
                      ))
                  .toList(),
            ),
          ),
        ),
      ],
    );
  }
}
