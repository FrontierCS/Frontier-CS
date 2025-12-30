#include <iostream>
#include <string>

using namespace std;

int main() {
    int m;
    // Read the number of passages per chamber.
    if (cin >> m) {
        string location;
        // Continuously read the location of the stone.
        // The loop terminates when the input is "treasure".
        while (cin >> location && location != "treasure") {
            // We implement a Rotor-Router walk.
            // "1 left 0" tells Indiana Jones to:
            // 1. Move the stone 1 passage clockwise relative to its current position.
            // 2. Place it on the "left" side (side choice is arbitrary but must be consistent).
            // 3. Take the passage at offset 0 relative to the stone's INITIAL position.
            // This ensures that for every visit to a chamber, we cycle through its passages
            // (0, 1, 2, ...) effectively visiting every edge in the graph.
            cout << "1 left 0" << endl;
        }
    }
    return 0;
}