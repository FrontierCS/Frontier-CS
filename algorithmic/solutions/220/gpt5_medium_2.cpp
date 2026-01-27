#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;
    vector<vector<int>> hand(n);
    for(int i=0;i<n;i++){
        hand[i].resize(n);
        for(int j=0;j<n;j++){
            cin >> hand[i][j];
        }
    }

    auto is_solved = [&]()->bool{
        for(int i=0;i<n;i++){
            for(int x: hand[i]){
                if(x != i+1) return false;
            }
        }
        return true;
    };

    vector<vector<int>> ops; // list of operations, each is vector of size n (labels passed by players 1..n)

    if(is_solved()){
        cout << 0 << "\n";
        return 0;
    }

    // stages s = n-1 down to 1
    for(int s = n-1; s >= 1; --s){
        for(int rep = 0; rep < n; ++rep){
            vector<int> chosen(n), idx(n);
            // choose cards simultaneously
            for(int i=0;i<n;i++){
                int target = ((i + s) % n) + 1; // desired label to send in this stage
                int pick = -1;
                // try to find target
                for(int k = 0; k < (int)hand[i].size(); ++k){
                    if(hand[i][k] == target){
                        pick = k;
                        break;
                    }
                }
                if(pick == -1){
                    // find any wrong card (label != i+1)
                    for(int k = 0; k < (int)hand[i].size(); ++k){
                        if(hand[i][k] != i+1){
                            pick = k;
                            break;
                        }
                    }
                }
                if(pick == -1){
                    // all correct, must send some (will be i+1)
                    pick = 0;
                }
                chosen[i] = hand[i][pick];
                idx[i] = pick;
            }
            // apply movement simultaneously
            for(int i=0;i<n;i++){
                int k = idx[i];
                int val = hand[i][k];
                // remove by swapping with last
                int last = hand[i].back();
                hand[i][k] = last;
                hand[i].pop_back();
            }
            for(int i=0;i<n;i++){
                int to = (i + 1) % n;
                hand[to].push_back(chosen[i]);
            }
            ops.push_back(chosen);
            if(is_solved()){
                cout << (int)ops.size() << "\n";
                for(auto &v: ops){
                    for(int i=0;i<n;i++){
                        if(i) cout << ' ';
                        cout << v[i];
                    }
                    cout << "\n";
                }
                return 0;
            }
        }
    }

    // After all stages, should be solved.
    cout << (int)ops.size() << "\n";
    for(auto &v: ops){
        for(int i=0;i<n;i++){
            if(i) cout << ' ';
            cout << v[i];
        }
        cout << "\n";
    }
    return 0;
}