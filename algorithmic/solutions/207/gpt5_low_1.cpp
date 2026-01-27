#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<int> S(N);
    for (int i = 0; i < N; ++i) cin >> S[i];
    int M;
    cin >> M;
    vector<pair<int,int>> J(M);
    for (int i = 0; i < M; ++i) {
        int x,y; cin >> x >> y;
        J[i] = {x,y};
    }
    
    vector<int> pos(N);
    for (int i = 0; i < N; ++i) pos[S[i]] = i;
    
    set<int> bad;
    for (int i = 0; i < N; ++i) if (S[i] != i) bad.insert(i);
    
    vector<pair<int,int>> myswaps;
    myswaps.reserve(M);
    long long sumdist = 0;
    int R = 0;
    
    auto upd_bad = [&](int idx){
        if (S[idx] != idx) bad.insert(idx);
        else bad.erase(idx);
    };
    
    if (bad.empty()) {
        cout << 0 << "\n";
        cout << 0 << "\n";
        return 0;
    }
    
    for (int k = 0; k < M; ++k) {
        // Jerry's move
        int x = J[k].first, y = J[k].second;
        if (x != y) {
            // update positions and array
            int vx = S[x], vy = S[y];
            swap(S[x], S[y]);
            pos[vx] = y;
            pos[vy] = x;
            upd_bad(x);
            upd_bad(y);
        }
        // Our move
        if (bad.empty()) {
            // already sorted; perform dummy swap and stop
            myswaps.emplace_back(0,0);
            sumdist += 0;
            R = k+1;
            break;
        } else {
            int i = *bad.begin();
            int j = pos[i];
            if (i == j) {
                // Shouldn't happen if bad not empty, but safeguard
                myswaps.emplace_back(0,0);
                sumdist += 0;
            } else {
                // perform swap i <-> j
                int vi = S[i], vj = S[j];
                swap(S[i], S[j]);
                pos[vi] = j;
                pos[vj] = i;
                upd_bad(i);
                upd_bad(j);
                myswaps.emplace_back(i,j);
                sumdist += llabs(i - j);
            }
        }
        if (bad.empty()) {
            R = k+1;
            break;
        }
    }
    
    if (!bad.empty()) {
        // Continue if we still have rounds left (shouldn't happen since R==0 here)
        // but we must output up to M moves; try to finish if possible in remaining rounds
        // We'll just output all moves we did; if none sorted, output full M with dummies to meet format (but choose R as len done).
        R = (int)myswaps.size();
    }
    
    cout << R << "\n";
    for (int i = 0; i < R; ++i) {
        cout << myswaps[i].first << " " << myswaps[i].second << "\n";
    }
    long long V = (long long)R * sumdist;
    cout << V << "\n";
    return 0;
}