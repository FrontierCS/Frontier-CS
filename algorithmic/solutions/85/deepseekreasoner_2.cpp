#include <iostream>
using namespace std;

int main() {
    int curDist;
    cin >> curDist;
    int lastMove = -1;  // color of the edge we arrived from, -1 initially

    while (curDist > 0) {
        // try the two colors that are not the one we came from
        for (int c = 0; c < 3; ++c) {
            if (c == lastMove) continue;

            // move along color c
            cout << "move " << c << endl;
            int moveResult;
            cin >> moveResult;
            if (moveResult == 1) {
                // reached the exit
                return 0;
            }

            // query the new distance
            cout << "query" << endl;
            int newDist;
            cin >> newDist;

            if (newDist < curDist) {
                // this move decreased the distance
                curDist = newDist;
                lastMove = c;  // remember the edge we used
                break;         // proceed to the next step
            } else {
                // this move increased the distance, move back
                cout << "move " << c << endl;
                cin >> moveResult;
                if (moveResult == 1) {
                    // reached the exit while moving back (unlikely but handled)
                    return 0;
                }
                // after moving back we are at the original node, distance unchanged
            }
        }
    }

    // If curDist becomes 0, we are already at the exit.
    return 0;
}