#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;
    vector<vector<int>> cnt(n, vector<int>(n+1,0));
    for(int i=0;i<n;i++){
        for(int j=0;j<n;j++){
            int x; cin >> x;
            cnt[i][x]++;
        }
    }
    vector<vector<int>> ops;
    // For each target number t, run n-1 steps pushing t-cards clockwise,
    // with owner t never passing t.
    for(int t=1; t<=n; ++t){
        for(int step=0; step<n-1; ++step){
            vector<int> pass(n, -1);
            // choose cards to pass
            for(int j=0;j<n;j++){
                if(j+1 != t && cnt[j][t] > 0){
                    pass[j] = t;
                }else{
                    // choose any card; prefer not to pass own-number if avoidable
                    int choose = -1;
                    for(int x=1;x<=n;x++){
                        if(x != j+1 && cnt[j][x] > 0){ choose = x; break; }
                    }
                    if(choose == -1){
                        // all cards are own-number
                        if(cnt[j][j+1] > 0) choose = j+1;
                        else{
                            // shouldn't happen, but fallback: find any available
                            for(int x=1;x<=n;x++){
                                if(cnt[j][x] > 0){ choose = x; break; }
                            }
                        }
                    }
                    pass[j] = choose;
                }
            }
            // apply transfers
            for(int j=0;j<n;j++){
                int d = pass[j];
                cnt[j][d]--;
                cnt[(j+1)%n][d]++;
            }
            ops.push_back(pass);
        }
    }
    cout << (int)ops.size() << "\n";
    for(auto &row: ops){
        for(int i=0;i<n;i++){
            if(i) cout << ' ';
            cout << row[i];
        }
        cout << "\n";
    }
    return 0;
}