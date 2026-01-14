#include <iostream>

using namespace std;

int main() {
    int h;
    cin >> h; // initial distance to exit

    while (h > 0) {
        for (int c = 0; c < 3; ++c) {
            // try moving along color c
            cout << "move " << c << endl;
            int result;
            cin >> result;
            if (result == 1) {
                // reached the exit
                return 0;
            }

            // query current distance
            cout << "query" << endl;
            int new_h;
            cin >> new_h;

            if (new_h == h - 1) {
                // moved to parent
                h = new_h;
                break;
            } else {
                // moved to a child, move back along the same color
                cout << "move " << c << endl;
                cin >> result;
                if (result == 1) {
                    // reached the exit on the way back
                    return 0;
                }
                // continue with next color
            }
        }
    }

    return 0;
}