#include <iostream>
#include <string>

using namespace std;

int main() {
    // The problem asks us to traverse a graph where nodes are indistinguishable
    // except for a stone we can place. This is a classic "robot on a graph"
    // problem. The "Rotor-Router" algorithm is a deterministic strategy that
    // guarantees visiting all edges in a strongly connected graph.
    //
    // Strategy:
    // In each chamber, we use the stone to point to the "next" passage to take.
    // When we arrive at a chamber:
    // 1. The stone is located at some passage (let's call its index 0 relative to itself).
    //    We interpret this as: "Passage 0 is the next passage to explore in the round-robin sequence".
    // 2. We proceed to take this passage (index 0).
    // 3. Before leaving, we move the stone to the next passage in clockwise order (index 1 relative to current).
    //    This ensures that next time we visit this chamber, we will take the next passage.
    //
    // If the stone is in the "center" (first visit), the origin is random. We arbitrarily
    // pick a passage as 0, take it, and place the stone at 1. This initializes the rotor.
    //
    // Command: "1 left 0"
    // "1": Move stone 1 position clockwise (from current stone position).
    // "left": Place the stone on the left side (side choice is arbitrary but must be consistent).
    // "0": Take passage 0 (relative to the stone position BEFORE moving it).
    
    int m;
    if (cin >> m) {
        string s;
        while (cin >> s && s != "treasure") {
            cout << "1 left 0" << endl;
        }
    }
    return 0;
}