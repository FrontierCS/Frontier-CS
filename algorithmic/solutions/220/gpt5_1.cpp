#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    vector<vector<int>> a(n, vector<int>(n));
    for(int i=0;i<n;i++){
        for(int j=0;j<n;j++) cin >> a[i][j];
    }
    // Fallback: output zero operations (valid only if already solved)
    // Check if already solved
    bool ok = true;
    for(int i=0;i<n;i++){
        for(int j=0;j<n;j++){
            if(a[i][j] != i+1) { ok = false; break; }
        }
        if(!ok) break;
    }
    if(ok){
        cout << 0 << "\n";
        return 0;
    }
    // As a last resort, try a simple heuristic pass up to n^2 - n operations:
    // Always pass a wrong card if possible, preferring one that moves closer.
    int T = n*(n-1);
    vector<vector<int>> cnt(n, vector<int>(n+1,0));
    for(int i=0;i<n;i++){
        for(int x: a[i]) cnt[i][x]++;
    }
    vector<vector<int>> ops;
    ops.reserve(T);
    for(int step=0; step<T; ++step){
        vector<int> pass(n, -1);
        // choose pass
        for(int i=0;i<n;i++){
            // prefer wrong card that gets closer (distance decreases by 1 when moving right)
            int bestLabel = -1;
            for(int lab=1; lab<=n; ++lab){
                if(cnt[i][lab]==0) continue;
                if(lab == i+1) continue; // correct, try avoid
                // distance to target seat i+1: d = (lab - (i+1) + n) % n
                int d = (lab - (i+1) + n) % n;
                if(d == 0) continue;
                // any wrong works, just pick first
                bestLabel = lab;
                break;
            }
            if(bestLabel == -1){
                // no wrong card, must pass correct
                if(cnt[i][i+1]>0) bestLabel = i+1;
                else{
                    // pick any available
                    for(int lab=1; lab<=n; ++lab){
                        if(cnt[i][lab]>0){ bestLabel = lab; break; }
                    }
                }
            }
            pass[i] = bestLabel;
        }
        // apply pass
        vector<int> incoming(n, 0);
        for(int i=0;i<n;i++){
            cnt[i][pass[i]]--;
            int r = (i+1) % n;
            incoming[r] = pass[i];
        }
        for(int i=0;i<n;i++){
            cnt[i][incoming[i]]++;
        }
        ops.push_back(pass);
        // check solved
        bool done = true;
        for(int i=0;i<n;i++){
            for(int lab=1; lab<=n; ++lab){
                if((lab==i+1 && cnt[i][lab]!=n) || (lab!=i+1 && cnt[i][lab]!=0)){
                    done = false; break;
                }
            }
            if(!done) break;
        }
        if(done) break;
    }
    cout << ops.size() << "\n";
    for(auto &v: ops){
        for(int i=0;i<n;i++){
            if(i) cout << ' ';
            cout << v[i];
        }
        cout << "\n";
    }
    return 0;
}