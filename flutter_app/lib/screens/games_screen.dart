import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';
import '../styles.dart';
import '../config.dart';

class GamesScreen extends StatefulWidget {
  const GamesScreen({super.key});
  @override
  State<GamesScreen> createState() => _GamesScreenState();
}

class _GamesScreenState extends State<GamesScreen> {
  int _view = 0; // 0=menu, 1=game
  String? roomCode;
  String? playerName;
  String? yourSymbol;
  String? currentTurn;
  String? status;
  String? winner;
  List<dynamic> board = List.filled(9, null);
  Map<String, int> scores = {'X': 0, 'O': 0};
  int gamesPlayed = 0;
  Map<String, dynamic> leaderboard = {};
  WebSocketChannel? channel;

  final hostNameCtrl = TextEditingController();
  final hostPasswordCtrl = TextEditingController();
  final joinCodeCtrl = TextEditingController();
  final joinNameCtrl = TextEditingController();
  final joinPasswordCtrl = TextEditingController();

  final List<String> emojis = [
    '😂',
    '😭',
    '😎',
    '😉',
    '😘',
    '😜',
    '😱',
    '👏',
    '🌹',
    '🏆'
  ];
  String? floatingEmoji;
  String? emojiSender;

  @override
  void dispose() {
    channel?.sink.close();
    hostNameCtrl.dispose();
    hostPasswordCtrl.dispose();
    joinCodeCtrl.dispose();
    joinNameCtrl.dispose();
    joinPasswordCtrl.dispose();
    super.dispose();
  }

  void _showSnack(String msg, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(msg),
        backgroundColor: error ? Colors.red : AppTheme.successGreen));
  }

  Future<void> _createRoom() async {
    try {
      final res = await http.post(EnvConfig.api('/api/games/create'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'game_type': 'tictactoe',
            'player_name': hostNameCtrl.text,
            'password': hostPasswordCtrl.text
          }));
      if (res.statusCode >= 200 && res.statusCode < 300) {
        final data = jsonDecode(res.body);
        _updateRoom(data['room']);
        setState(() {
          roomCode = data['room_code'];
          playerName = hostNameCtrl.text;
          yourSymbol = 'X';
          _view = 1;
        });
        _connectWs();
        _showSnack('Room created! Code: $roomCode');
      }
    } catch (e) {
      _showSnack('Error: $e', error: true);
    }
  }

  Future<void> _joinRoom() async {
    final code = joinCodeCtrl.text.trim().toUpperCase();
    try {
      final res = await http.post(EnvConfig.api('/api/games/join/$code'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'player_name': joinNameCtrl.text,
            'password': joinPasswordCtrl.text
          }));
      if (res.statusCode >= 200 && res.statusCode < 300) {
        final data = jsonDecode(res.body);
        _updateRoom(data['room']);
        setState(() {
          roomCode = code;
          playerName = joinNameCtrl.text;
          yourSymbol = 'O';
          _view = 1;
        });
        _connectWs();
        _showSnack('Joined game!');
      } else {
        _showSnack('Invalid code or password', error: true);
      }
    } catch (e) {
      _showSnack('Error: $e', error: true);
    }
  }

  void _connectWs() {
    if (roomCode == null) return;
    channel?.sink.close();
    channel = WebSocketChannel.connect(EnvConfig.ws('/ws/$roomCode'));
    channel!.stream.listen((event) {
      try {
        final data = jsonDecode(event as String);
        if (data['type'] == 'game_move' ||
            data['type'] == 'player_joined' ||
            data['type'] == 'game_restarted') {
          _updateRoom(data['room']);
        } else if (data['type'] == 'emoji_reaction') {
          _showFloatingEmoji(data['player_name'], data['emoji']);
        }
      } catch (_) {}
    });
  }

  void _updateRoom(Map<String, dynamic>? room) {
    if (room == null) return;
    setState(() {
      board = List.from(room['board'] ?? List.filled(9, null));
      currentTurn = room['current_turn'];
      status = room['status'];
      winner = room['winner'];
      scores = {'X': room['scores']?['X'] ?? 0, 'O': room['scores']?['O'] ?? 0};
      gamesPlayed = room['games_played'] ?? 0;
      leaderboard = room['leaderboard'] ?? {};
    });
  }

  Future<void> _makeMove(int idx) async {
    if (board[idx] != null || status != 'playing' || currentTurn != yourSymbol) {
      return;
    }
    try {
      final res = await http.post(EnvConfig.api('/api/games/move'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(
              {'room_code': roomCode, 'player_name': playerName, 'move': idx}));
      if (res.statusCode >= 200 && res.statusCode < 300) {
        _updateRoom(jsonDecode(res.body)['room']);
      }
    } catch (_) {}
  }

  Future<void> _sendEmoji(String emoji) async {
    try {
      await http.post(EnvConfig.api('/api/games/emoji'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'room_code': roomCode,
            'player_name': playerName,
            'emoji': emoji
          }));
    } catch (_) {}
  }

  void _showFloatingEmoji(String sender, String emoji) {
    setState(() {
      floatingEmoji = emoji;
      emojiSender = sender;
    });
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) {
        setState(() {
          floatingEmoji = null;
          emojiSender = null;
        });
      }
    });
  }

  Future<void> _requestRestart() async {
    try {
      await http.post(EnvConfig.api('/api/games/restart'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'room_code': roomCode, 'player_name': playerName}));
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: AppTheme.gradientBackground(AppTheme.gamesGradient),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
            backgroundColor: Colors.transparent, title: const Text('🎮 Games')),
        body: _view == 0 ? _buildMenu() : _buildGame(),
      ),
    );
  }

  Widget _buildMenu() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(children: [
        _card('🎯 Create Game Room', [
          TextField(
              controller: hostNameCtrl,
              decoration: AppTheme.inputDecoration('Your Name')),
          const SizedBox(height: 12),
          TextField(
              controller: hostPasswordCtrl,
              obscureText: true,
              decoration: AppTheme.inputDecoration('Password')),
          const SizedBox(height: 16),
          ElevatedButton(
              onPressed: _createRoom,
              style: AppTheme.primaryButton,
              child: const Text('Create Room')),
        ]),
        const SizedBox(height: 20),
        _card('🎲 Join Game', [
          TextField(
              controller: joinCodeCtrl,
              decoration: AppTheme.inputDecoration('Game Code')),
          const SizedBox(height: 12),
          TextField(
              controller: joinNameCtrl,
              decoration: AppTheme.inputDecoration('Your Name')),
          const SizedBox(height: 12),
          TextField(
              controller: joinPasswordCtrl,
              obscureText: true,
              decoration: AppTheme.inputDecoration('Password')),
          const SizedBox(height: 16),
          ElevatedButton(
              onPressed: _joinRoom,
              style: AppTheme.secondaryButton,
              child: const Text('Join')),
        ]),
      ]),
    );
  }

  Widget _card(String title, List<Widget> children) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 10)]),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text(title,
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 16),
        ...children
      ]),
    );
  }

  Widget _buildGame() {
    final isYourTurn = currentTurn == yourSymbol;
    return Stack(
      children: [
        Column(children: [
          // Scoreboard
          Container(
            margin: const EdgeInsets.all(16),
            padding: const EdgeInsets.all(16),
            decoration: AppTheme.scoreboardCard,
            child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  Column(children: [
                    Text('X',
                        style: TextStyle(
                            fontSize: 28,
                            fontWeight: FontWeight.bold,
                            color: currentTurn == 'X'
                                ? Colors.blue
                                : Colors.grey)),
                    Text('${scores['X']}', style: const TextStyle(fontSize: 24))
                  ]),
                  Column(children: [
                    const Text('VS',
                        style: TextStyle(fontSize: 16, color: Colors.grey)),
                    Text('Round ${gamesPlayed + 1}',
                        style:
                            const TextStyle(fontSize: 12, color: Colors.grey))
                  ]),
                  Column(children: [
                    Text('O',
                        style: TextStyle(
                            fontSize: 28,
                            fontWeight: FontWeight.bold,
                            color:
                                currentTurn == 'O' ? Colors.red : Colors.grey)),
                    Text('${scores['O']}', style: const TextStyle(fontSize: 24))
                  ]),
                ]),
          ),
          // Turn indicator
          Text(
              status == 'waiting'
                  ? 'Waiting for opponent...'
                  : status == 'playing'
                      ? (isYourTurn ? 'Your turn!' : "Opponent's turn")
                      : winner != null
                          ? '${winner == yourSymbol ? "You" : "Opponent"} won!'
                          : 'Draw!',
              style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: isYourTurn ? Colors.green : Colors.grey)),
          const SizedBox(height: 16),
          // Game Board
          Container(
            padding: const EdgeInsets.all(8),
            child: GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 3, crossAxisSpacing: 8, mainAxisSpacing: 8),
              itemCount: 9,
              itemBuilder: (_, idx) {
                final v = board[idx];
                return InkWell(
                  onTap: () => _makeMove(idx),
                  child: Container(
                    decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                            color: v == 'X'
                                ? Colors.blue
                                : v == 'O'
                                    ? Colors.red
                                    : Colors.grey.shade300,
                            width: 3)),
                    child: Center(
                        child: Text(v ?? '',
                            style: TextStyle(
                                fontSize: 48,
                                fontWeight: FontWeight.bold,
                                color: v == 'X' ? Colors.blue : Colors.red))),
                  ),
                );
              },
            ),
          ),
          // Play Again
          if (status == 'finished' || status == 'draw')
            Padding(
                padding: const EdgeInsets.all(16),
                child: ElevatedButton.icon(
                    onPressed: _requestRestart,
                    style: AppTheme.primaryButton,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Play Again'))),
          // Emoji Panel
          const SizedBox(height: 8),
          const Text('Send Reaction',
              style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Wrap(
              spacing: 8,
              runSpacing: 8,
              children: emojis
                  .map((e) => InkWell(
                      onTap: () => _sendEmoji(e),
                      child: Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(8)),
                          child:
                              Text(e, style: const TextStyle(fontSize: 24)))))
                  .toList()),
        ]),
        // Floating emoji
        if (floatingEmoji != null)
          Center(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
            Text(floatingEmoji!, style: const TextStyle(fontSize: 80)),
            Text(emojiSender ?? '',
                style: const TextStyle(fontSize: 14, color: Colors.grey))
          ])),
      ],
    );
  }
}
