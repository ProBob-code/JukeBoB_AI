import 'package:flutter_test/flutter_test.dart';

import 'package:jukebob_flutter/main.dart';

void main() {
  testWidgets('App builds and shows JUKEBOB title',
      (WidgetTester tester) async {
    // Build the app and trigger a frame.
    await tester.pumpWidget(const JukeBoBApp());

    // Wait for any async builds/animations to settle.
    await tester.pumpAndSettle();

    // Expect the main title 'JUKEBOB' to be present somewhere in the widget tree.
    expect(find.text('JUKEBOB'), findsOneWidget);

    // Optional: also check that one of your section labels exist (e.g., 'Jukebox').
    expect(find.text('Jukebox'), findsWidgets);
  });
}
