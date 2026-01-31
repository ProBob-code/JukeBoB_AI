import 'package:flutter/material.dart';

class AppTheme {
  static const Color brandYellow = Color(0xFFFFC107);
  static const Color vipGold = Color(0xFFFFD700);
  static const Color successGreen = Color(0xFF4CAF50);
  static const Color dangerRed = Color(0xFFE53935);
  static const Color darkBg = Color(0xFF1A1A2E);

  static const Gradient homeGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFF5D547), Color(0xFFFFC107)],
  );

  static const Gradient jukeboxGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF0F0C29), Color(0xFF302B63), Color(0xFF24243E)],
  );

  static const Gradient gamesGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFFFECD2), Color(0xFFFcb69F)],
  );

  static const Gradient aiDjGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF141E30), Color(0xFF243B55)],
  );

  // VIP card gradient for high-tip songs
  static const Gradient vipCardGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFFFD700), Color(0xFFFFA500)],
  );

  static BoxDecoration gradientBackground(Gradient gradient) =>
      BoxDecoration(gradient: gradient);

  // Input decoration for text fields
  static InputDecoration inputDecoration(String label, {IconData? prefixIcon}) {
    return InputDecoration(
      labelText: label,
      labelStyle: const TextStyle(color: Colors.grey),
      filled: true,
      fillColor: Colors.white,
      prefixIcon:
          prefixIcon != null ? Icon(prefixIcon, color: Colors.grey) : null,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide.none,
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: brandYellow, width: 2),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
    );
  }

  // Primary button style
  static ButtonStyle primaryButton = ElevatedButton.styleFrom(
    backgroundColor: brandYellow,
    foregroundColor: Colors.black87,
    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    elevation: 4,
    textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
  );

  // Secondary button style
  static ButtonStyle secondaryButton = ElevatedButton.styleFrom(
    backgroundColor: Colors.white,
    foregroundColor: Colors.black87,
    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    elevation: 2,
    textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
  );

  // Tertiary/outline button style
  static ButtonStyle tertiaryButton = OutlinedButton.styleFrom(
    foregroundColor: brandYellow,
    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    side: const BorderSide(color: brandYellow, width: 2),
    textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
  );

  // Danger button style (for skip/delete actions)
  static ButtonStyle dangerButton = ElevatedButton.styleFrom(
    backgroundColor: dangerRed,
    foregroundColor: Colors.white,
    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    elevation: 4,
  );

  // Success button style
  static ButtonStyle successButton = ElevatedButton.styleFrom(
    backgroundColor: successGreen,
    foregroundColor: Colors.white,
    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    elevation: 4,
  );

  // Card decoration for stats
  static BoxDecoration statsCard = BoxDecoration(
    color: Colors.white.withOpacity(0.15),
    borderRadius: BorderRadius.circular(16),
    border: Border.all(color: Colors.white24),
  );

  // VIP song card decoration
  static BoxDecoration vipSongCard = BoxDecoration(
    gradient: vipCardGradient,
    borderRadius: BorderRadius.circular(12),
    boxShadow: [
      BoxShadow(
        color: vipGold.withOpacity(0.4),
        blurRadius: 12,
        offset: const Offset(0, 4),
      ),
    ],
  );

  // Regular song card decoration
  static BoxDecoration regularSongCard = BoxDecoration(
    color: Colors.white.withOpacity(0.1),
    borderRadius: BorderRadius.circular(12),
    border: Border.all(color: Colors.white24),
  );

  // Scoreboard card decoration
  static BoxDecoration scoreboardCard = BoxDecoration(
    color: Colors.white,
    borderRadius: BorderRadius.circular(20),
    boxShadow: [
      BoxShadow(
        color: Colors.black.withOpacity(0.1),
        blurRadius: 20,
        offset: const Offset(0, 8),
      ),
    ],
  );

  // Emoji button style
  static ButtonStyle emojiButton = ElevatedButton.styleFrom(
    backgroundColor: Colors.white,
    foregroundColor: Colors.black,
    padding: const EdgeInsets.all(12),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    elevation: 2,
    minimumSize: const Size(50, 50),
  );

  // Turntable/deck decoration for AI DJ
  static BoxDecoration turntableDeck = BoxDecoration(
    color: const Color(0xFF1A1A2E),
    borderRadius: BorderRadius.circular(20),
    border: Border.all(color: const Color(0xFF00D4FF), width: 2),
    boxShadow: [
      BoxShadow(
        color: const Color(0xFF00D4FF).withOpacity(0.3),
        blurRadius: 20,
        spreadRadius: 2,
      ),
    ],
  );

  // Section card widget
  static Widget sectionCard({
    required BuildContext context,
    required String title,
    required String subtitle,
    required String emoji,
    required VoidCallback onTap,
    required List<Color> colors,
  }) {
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(28),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(32),
          gradient: LinearGradient(
              colors: colors,
              begin: Alignment.topLeft,
              end: Alignment.bottomRight),
          boxShadow: [
            BoxShadow(
                color: Colors.black.withOpacity(0.2),
                blurRadius: 20,
                offset: const Offset(0, 10)),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(emoji, style: const TextStyle(fontSize: 40)),
            const SizedBox(height: 10),
            Text(title,
                style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                    color: Colors.white,
                    shadows: [
                      Shadow(
                          color: Colors.black26,
                          offset: Offset(0, 2),
                          blurRadius: 4)
                    ])),
            const SizedBox(height: 6),
            Text(subtitle,
                style: const TextStyle(
                    color: Colors.white, fontSize: 14, height: 1.2)),
          ],
        ),
      ),
    );
  }

  // Stats card widget for jukebox dashboard
  static Widget statsCardWidget({
    required String value,
    required String label,
    Color? valueColor,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: statsCard,
      child: Column(
        children: [
          Text(
            value,
            style: TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.bold,
              color: valueColor ?? Colors.white,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              color: Colors.white.withOpacity(0.7),
            ),
          ),
        ],
      ),
    );
  }

  // VIP badge widget
  static Widget vipBadge() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        gradient: vipCardGradient,
        borderRadius: BorderRadius.circular(12),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('👑', style: TextStyle(fontSize: 12)),
          SizedBox(width: 4),
          Text(
            'VIP',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.bold,
              color: Colors.black87,
            ),
          ),
        ],
      ),
    );
  }

  // Song request card
  static Widget songCard({
    required String songName,
    required String artist,
    required String requester,
    required double tipAmount,
    required String status,
    bool isHost = false,
    VoidCallback? onComplete,
    VoidCallback? onSkip,
  }) {
    final isVip = tipAmount >= 10;
    final isQueued = status == 'queued';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: isVip ? vipSongCard : regularSongCard,
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (isVip) const Text('👑', style: TextStyle(fontSize: 24)),
            if (!isVip) const Text('🎵', style: TextStyle(fontSize: 24)),
          ],
        ),
        title: Text(
          songName,
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: isVip ? Colors.black87 : Colors.white,
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              artist,
              style: TextStyle(
                color: isVip ? Colors.black54 : Colors.white70,
              ),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Text(
                  'by $requester',
                  style: TextStyle(
                    fontSize: 12,
                    color: isVip ? Colors.black45 : Colors.white54,
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: isVip ? Colors.black12 : Colors.white12,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '₹${tipAmount.toStringAsFixed(0)}',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: isVip ? Colors.black87 : Colors.white,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
        trailing: isHost && isQueued
            ? Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  IconButton(
                    onPressed: onComplete,
                    icon: Icon(
                      Icons.check_circle,
                      color: isVip ? successGreen : Colors.green,
                      size: 28,
                    ),
                  ),
                  IconButton(
                    onPressed: onSkip,
                    icon: Icon(
                      Icons.cancel,
                      color: isVip ? dangerRed : Colors.red,
                      size: 28,
                    ),
                  ),
                ],
              )
            : status != 'queued'
                ? Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: status == 'completed' ? successGreen : Colors.grey,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      status == 'completed' ? '✓ Played' : status,
                      style: const TextStyle(
                        fontSize: 10,
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  )
                : null,
      ),
    );
  }
}
