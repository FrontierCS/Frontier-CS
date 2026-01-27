#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

void solve() {
    int n;
    if (!(cin >> n)) return;
    int N = n * n;
    
    // S stores the current candidates for the maximum speed
    vector<int> S;
    // hidden[i] stores the list of pepes directly defeated by pepe i
    vector<vector<int>> hidden(N + 1);

    // Initial Phase: partition the n^2 pepes into n groups of n and race them.
    // This reduces the number of candidates to n.
    for (int i = 1; i <= N; i += n) {
        cout << "?";
        for (int j = 0; j < n; ++j) {
            cout << " " << (i + j);
        }
        cout << endl;
        int winner;
        cin >> winner;
        S.push_back(winner);
        for (int j = 0; j < n; ++j) {
            int curr = i + j;
            if (curr != winner) {
                hidden[winner].push_back(curr);
            }
        }
    }

    vector<int> result;
    // We need to determine the n^2 - n + 1 fastest pepes
    int target = N - n + 1;

    while (result.size() < target) {
        // While there is more than 1 candidate for the current max, perform races to reduce candidates
        while (S.size() > 1) {
            vector<int> batch;
            vector<int> next_S;
            
            if (S.size() >= n) {
                // If we have enough candidates to form a full race, pick n of them
                for (int i = 0; i < n; ++i) batch.push_back(S[i]);
                for (size_t i = n; i < S.size(); ++i) next_S.push_back(S[i]);
                
                cout << "?";
                for (int x : batch) cout << " " << x;
                cout << endl;
                
                int winner;
                cin >> winner;
                
                // The winner remains a candidate, losers are moved to hidden[winner]
                next_S.push_back(winner);
                for (int x : batch) {
                    if (x != winner) {
                        hidden[winner].push_back(x);
                    }
                }
                S = next_S;
            } else {
                // If fewer than n candidates, we need to pad the race with already defeated pepes.
                // We pick pepes from the hidden lists of the current candidates.
                // Since hidden pepes are dominated by candidates, the winner will still be from S.
                batch = S;
                int needed = n - batch.size();
                vector<int> padding;
                
                for (int s : S) {
                    if (padding.size() >= needed) break;
                    for (int h : hidden[s]) {
                        padding.push_back(h);
                        if (padding.size() >= needed) break;
                    }
                }
                
                cout << "?";
                for (int x : batch) cout << " " << x;
                for (int x : padding) cout << " " << x;
                cout << endl;
                
                int winner;
                cin >> winner;
                
                // Winner must be from batch.
                // Losers from batch move to hidden[winner].
                next_S.clear();
                next_S.push_back(winner);
                for (int x : batch) {
                    if (x != winner) {
                        hidden[winner].push_back(x);
                    }
                }
                S = next_S;
            }
        }
        
        // S has exactly 1 element, which is the global maximum of the remaining pepes
        int best = S[0];
        result.push_back(best);
        S.clear();
        
        // The pepes that were directly defeated by 'best' now become candidates
        for (int x : hidden[best]) {
            S.push_back(x);
        }
    }

    cout << "!";
    for (int x : result) cout << " " << x;
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}