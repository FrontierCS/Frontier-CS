#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Global variables for problem state
const int MAX_N = 405; // 20^2 = 400
vector<int> children[MAX_N];
bool is_outputted[MAX_N];
bool is_in_H[MAX_N];

void solve() {
    int n;
    if (!(cin >> n)) return;
    int total_pepes = n * n;

    // Reset state for each test case
    for (int i = 1; i <= total_pepes; ++i) {
        children[i].clear();
        is_outputted[i] = false;
        is_in_H[i] = false;
    }

    // Initially, all pepes are candidates (roots) for the global maximum.
    // H stores the set of current candidate roots.
    vector<int> H;
    for (int i = 1; i <= total_pepes; ++i) {
        H.push_back(i);
        is_in_H[i] = true;
    }

    // We need to determine the top n^2 - n + 1 pepes
    int to_output = total_pepes - n + 1;
    vector<int> result;

    for (int iter = 0; iter < to_output; ++iter) {
        // We maintain a set H of "roots". The global maximum among un-outputted pepes
        // is guaranteed to be in H. We perform races to reduce H to a single element.
        while (H.size() > 1) {
            // Prepare a race with up to n candidates from H
            vector<int> race_pepes;
            vector<int> from_H;
            
            // Take candidates from H
            while (from_H.size() < n && !H.empty()) {
                from_H.push_back(H.back());
                H.pop_back();
            }
            
            // Add them to the race list
            for (int x : from_H) race_pepes.push_back(x);
            
            // If we have fewer than n candidates in the race, we need to pad with "dummy" participants.
            // We can use any un-outputted pepe that is NOT currently a root (i.e., is dominated by someone).
            // This ensures we don't interfere with the winner logic if the true max is in from_H.
            if (race_pepes.size() < n) {
                int needed = n - race_pepes.size();
                for (int i = 1; i <= total_pepes && needed > 0; ++i) {
                    // Pick any node that is not outputted and not currently a root.
                    // Note: elements in from_H still have is_in_H = true.
                    if (!is_outputted[i] && !is_in_H[i]) {
                        race_pepes.push_back(i);
                        needed--;
                    }
                }
            }
            
            // Perform the query
            cout << "?";
            for (int x : race_pepes) cout << " " << x;
            cout << endl;
            
            int winner;
            cin >> winner;
            
            // Determine if the winner was one of the roots we tested
            bool winner_is_root = false;
            for (int x : from_H) {
                if (x == winner) {
                    winner_is_root = true;
                    break;
                }
            }
            
            if (winner_is_root) {
                // The winner is from H, so it remains a root. We put it back.
                H.push_back(winner);
                // All other roots in this race lost to the winner, so they become its children
                // and are no longer roots (removed from H).
                for (int x : from_H) {
                    if (x != winner) {
                        children[winner].push_back(x);
                        is_in_H[x] = false;
                    }
                }
            } else {
                // The winner was a padding element (a descendant of some other root).
                // This implies all roots in from_H are slower than this pad, and thus slower than the pad's ancestor.
                // They become children of the winner (or effectively dominated by the winner's chain).
                // They are removed from H.
                for (int x : from_H) {
                    children[winner].push_back(x);
                    is_in_H[x] = false;
                }
                // The winner is NOT added to H because it is not a root (it's dominated by someone else in H).
            }
        }
        
        // Now H contains exactly 1 element, which is the maximum of all available pepes.
        int best = H[0];
        result.push_back(best);
        is_outputted[best] = true;
        is_in_H[best] = false;
        H.clear();
        
        // The children of the removed max become new candidates (roots).
        for (int child : children[best]) {
            H.push_back(child);
            is_in_H[child] = true;
        }
    }

    // Output the result
    cout << "!";
    for (int x : result) cout << " " << x;
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}