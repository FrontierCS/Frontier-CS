#include <iostream>
#include <string>
#include <vector>

// Global state for the state machine.
// m: number of passages in each chamber.
int m;
// k: a counter for the number of passages taken from the currently 'active' chamber(s).
// 'active' chambers are marked 'left'.
int k = 0;

void solve() {
    // First, read the number of passages per chamber.
    std::cin >> m;

    std::string state;
    // Loop for interaction until the treasure is found.
    while (std::cin >> state && state != "treasure") {
        if (state == "center") {
            // This is a new, unvisited chamber.
            // We start exploring it by taking one passage and marking the chamber 'left'.
            // Action: `0 left 0`
            // - `d=0`: Place the stone relative to the current (random) reference passage.
            // - `s=left`: Mark the chamber as "in progress".
            // - `p=0`: Take the reference passage itself.
            // This establishes the taken passage as the canonical passage 0 for this chamber.
            // We have now taken 1 passage from this chamber, so we set our counter k to 1.
            k = 1;
            std::cout << "0 left 0" << std::endl;

        } else if (state == "left") {
            // This is a chamber currently being explored.
            // Our counter `k` indicates we have already taken `k` passages from it.
            // The stone is at passage `k-1`, which is our current reference.
            // We need to take the next passage, `k`, and move the stone mark to it.
            // Passage `k` is 1 position clockwise from passage `k-1` (our reference).
            
            if (k < m - 1) {
                // Not the last passage. Take the next one and keep the mark 'left'.
                // Action: `1 left 1`
                // - `d=1`: Move the stone one passage clockwise (to passage `k`).
                // - `s=left`: Keep the mark as "in progress".
                // - `p=1`: Take the passage one clockwise from the reference (passage `k`).
                std::cout << "1 left 1" << std::endl;
            } else {
                // This is the last passage to explore from this chamber (passage m-1).
                // After taking it, the chamber will be fully explored. Mark it 'right'.
                // Action: `1 right 1`
                // - `d=1`: Move the stone to the last passage.
                // - `s=right`: Mark the chamber as "fully explored".
                // - `p=1`: Take the last passage.
                std::cout << "1 right 1" << std::endl;
            }
            // Increment the count of passages taken from an active chamber.
            k++;

        } else if (state == "right") {
            // This is a fully explored chamber. We just need to pass through.
            // We take a passage without changing the mark. Taking the marked passage
            // itself (local passage 0) is a simple, consistent choice.
            // Action: `0 right 0`
            // - `d=0`: Don't move the stone.
            // - `s=right`: Keep the mark as "fully explored".
            // - `p=0`: Take the marked passage.
            std::cout << "0 right 0" << std::endl;
        }
    }
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(nullptr);

    solve();

    return 0;
}