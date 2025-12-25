#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Helper function to test adjacency between two nodes.
// Returns true if x and y are adjacent.
// Assumes the current set S is empty before the call, and leaves S empty after.
bool adj(int x, int y) {
    cout << "4 " << x << " " << y << " " << x << " " << y << endl;
    cout.flush();
    int a, b, c, d;
    cin >> a >> b >> c >> d;
    return b == 1;
}

// Helper function to test adjacency of x to both a and b.
// Returns a pair (adjacent_to_a, adjacent_to_b).
// Assumes S is empty before the call, and leaves S empty after.
pair<bool, bool> adj2(int x, int a, int b) {
    cout << "6 " << x << " " << a << " " << a << " " << b << " " << b << " " << x << endl;
    cout.flush();
    int r[6];
    for (int i = 0; i < 6; ++i) cin >> r[i];
    return {r[1] == 1, r[3] == 1};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int subtask, n;
    cin >> subtask >> n;

    // Random generator for shuffling
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    vector<int> chain;
    chain.push_back(1);  // start with node 1

    vector<int> rem;
    for (int i = 2; i <= n; ++i) rem.push_back(i);

    bool is_cycle = false;

    while (!rem.empty()) {
        // Shuffle remaining nodes to avoid worst-case order
        shuffle(rem.begin(), rem.end(), rng);

        bool attached = false;
        for (size_t idx = 0; idx < rem.size(); ++idx) {
            int x = rem[idx];
            if (chain.size() == 1) {
                // Only one node in chain
                if (adj(x, chain[0])) {
                    chain.push_back(x);
                    rem.erase(rem.begin() + idx);
                    attached = true;
                    break;
                }
            } else {
                int left = chain.front();
                int right = chain.back();
                auto [adjL, adjR] = adj2(x, left, right);
                if (adjL && adjR) {
                    // Closing the cycle
                    chain.push_back(x);
                    rem.erase(rem.begin() + idx);
                    is_cycle = true;
                    attached = true;
                    break;
                } else if (adjL) {
                    chain.insert(chain.begin(), x);
                    rem.erase(rem.begin() + idx);
                    attached = true;
                    break;
                } else if (adjR) {
                    chain.push_back(x);
                    rem.erase(rem.begin() + idx);
                    attached = true;
                    break;
                }
            }
        }
        if (!attached) {
            // This should not happen if the chain is maintained correctly
            // but in case of error, we break to avoid infinite loop
            break;
        }
    }

    // Output the guessed permutation
    cout << "-1";
    for (int v : chain) cout << " " << v;
    cout << endl;
    cout.flush();

    return 0;
}