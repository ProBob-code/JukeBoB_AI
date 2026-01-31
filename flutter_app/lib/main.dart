import 'package:flutter/material.dart';
import 'styles.dart';
import 'screens/jukebox_screen.dart';
import 'screens/games_screen.dart';
import 'screens/aidj_screen.dart';

void main() {
  runApp(const JukeBoBApp());
}

class JukeBoBApp extends StatelessWidget {
  const JukeBoBApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'JUKEBOB',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: AppTheme.brandYellow),
        useMaterial3: true,
        scaffoldBackgroundColor: Colors.transparent,
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.transparent,
          elevation: 0,
          titleTextStyle: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
      ),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: AppTheme.gradientBackground(AppTheme.homeGradient),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          centerTitle: false,
          title: Row(
            children: [
              Image.asset('assets/icon.png', height: 28),
              const SizedBox(width: 8),
              const Text('JUKEBOB', style: TextStyle(color: Colors.black87)),
            ],
          ),
        ),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Center(
                child: Column(
                  children: [
                    const SizedBox(height: 8),
                    Container(
                      decoration: BoxDecoration(
                        color: const Color(0xFFFFD84D),
                        borderRadius: BorderRadius.circular(12),
                        boxShadow: const [
                          BoxShadow(
                              color: Colors.black12,
                              blurRadius: 16,
                              offset: Offset(0, 6))
                        ],
                      ),
                      padding: const EdgeInsets.all(16),
                      child: Image.asset('assets/logo.png', height: 180),
                    ),
                    const SizedBox(height: 24),
                    const Text(
                      'JUKEBOB',
                      style: TextStyle(
                        fontSize: 40,
                        fontWeight: FontWeight.w900,
                        color: Colors.black87,
                        shadows: [
                          Shadow(
                              color: Colors.black26,
                              offset: Offset(0, 3),
                              blurRadius: 6)
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'Your Ultimate Party Entertainment Hub',
                      style: TextStyle(fontSize: 16, color: Colors.black87),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 20),
                  ],
                ),
              ),
              Expanded(
                child: GridView.count(
                  crossAxisCount: 1,
                  childAspectRatio: 2.3,
                  mainAxisSpacing: 20,
                  children: [
                    AppTheme.sectionCard(
                      context: context,
                      title: 'Jukebox',
                      subtitle:
                          'Crowd-controlled music requests, voting & tipping',
                      emoji: '🎵',
                      onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (_) => const JukeboxScreen())),
                      colors: const [Color(0xFFF093FB), Color(0xFFF5576C)],
                    ),
                    AppTheme.sectionCard(
                      context: context,
                      title: 'Games',
                      subtitle: 'Play Tic Tac Toe, Mafia & more',
                      emoji: '🎮',
                      onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (_) => const GamesScreen())),
                      colors: const [Color(0xFFFFECD2), Color(0xFFFcb69F)],
                    ),
                    AppTheme.sectionCard(
                      context: context,
                      title: 'AI DJ',
                      subtitle: 'Smart mixing with dual turntables',
                      emoji: '🎧',
                      onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (_) => const AiDjScreen())),
                      colors: const [Color(0xFF00D4FF), Color(0xFF0099CC)],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
