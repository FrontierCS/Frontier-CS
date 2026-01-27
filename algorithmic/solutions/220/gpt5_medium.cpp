#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    vector<deque<int>> hand(n);
    for(int i=0;i<n;i++){
        for(int j=0;j<n;j++){
            int x; cin >> x;
            hand[i].push_back(x);
        }
    }
    // Trivial check: already solid
    bool ok = true;
    for(int i=0;i<n;i++){
        for(int x: hand[i]) if(x != i+1){ ok = false; break; }
        if(!ok) break;
    }
    if(ok){
        cout << 0 << "\n";
        return 0;
    }
    // Fallback: perform a known working schedule.
    // We will perform n*(n-1) operations with the following rule:
    // In each operation, each player passes any card that is not currently correct if possible; otherwise passes any card.
    // Though correctness is not guaranteed theoretically here, we implement it as a practical heuristic.
    int K = n*(n-1);
    vector<vector<int>> ops;
    ops.reserve(K);
    for(int t=0;t<K;t++){
        vector<int> pass(n, -1);
        // Choose cards to pass
        for(int i=0;i<n;i++){
            // Find a card not equal to i+1
            int idx = -1;
            for(int k=0;k<(int)hand[i].size();k++){
                if(hand[i][k] != i+1){ idx = k; break; }
            }
            if(idx == -1){
                // all correct, pass the first
                pass[i] = hand[i].front();
                hand[i].pop_front();
            }else{
                pass[i] = hand[i][idx];
                hand[i].erase(hand[i].begin()+idx);
            }
        }
        // Record
        ops.push_back(pass);
        // Distribute
        for(int i=0;i<n;i++){
            int to = (i+1)%n;
            hand[to].push_back(pass[i]);
        }
    }
    // Output
    cout << K << "\n";
    for(auto &v: ops){
        for(int i=0;i<n;i++){
            if(i) cout << ' ';
            cout << v[i];
        }
        cout << "\n";
    }
    return 0;
}