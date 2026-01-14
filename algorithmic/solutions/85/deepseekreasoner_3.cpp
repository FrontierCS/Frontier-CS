#include <iostream>
#include <cstdlib>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int d;
    cin >> d;
    if (d == 0) {
        // already at exit
        return 0;
    }

    int banned = -1; // color of the edge leading to the child we came from (if any)
    while (true) {
        for (int c = 0; c < 3; ++c) {
            if (c == banned) continue;

            // try edge c
            cout << "move " << c << endl;
            int reached;
            cin >> reached;
            if (reached == 1) {
                // reached the exit
                return 0;
            }

            cout << "query" << endl;
            int new_d;
            cin >> new_d;
            if (new_d == 0) {
                // reached the exit (according to query)
                return 0;
            }

            if (new_d == d - 1) {
                // moved to parent
                d = new_d;
                banned = c; // at the new node, edge c leads to the child we came from
                break; // exit the for loop, continue while loop
            } else if (new_d == d + 1) {
                // moved to a child, move back using the same edge color
                cout << "move " << c << endl;
                cin >> reached;
                if (reached == 1) {
                    // reached the exit while moving back (possible if d was 1)
                    return 0;
                }
                // now back at the original node
                banned = c; // we now know that edge c leads to a child
                continue; // try the next color
            } else {
                // Unexpected distance change – should not happen with a valid tree.
                // Fallback: treat as child and move back (or abort).
                // For safety, we move back and mark as child.
                cout << "move " << c << endl;
                cin >> reached;
                if (reached == 1) return 0;
                banned = c;
            }
        }
    }
    return 0;
}