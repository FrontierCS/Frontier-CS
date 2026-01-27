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
        int x, y;
        cin >> x >> y;
        J[i] = {x, y};
    }
    vector<int> pos(N);
    for (int i = 0; i < N; ++i) pos[S[i]] = i;
    // set of mismatched indices
    set<int> bad;
    for (int i = 0; i < N; ++i) if (S[i] != i) bad.insert(i);
    
    auto updateBad = [&](int idx){
        if (S[idx] == idx) {
            bad.erase(idx);
        } else {
            bad.insert(idx);
        }
    };
    
    vector<pair<int,int>> moves;
    moves.reserve(M);
    long long sumDist = 0;
    
    for (int k = 0; k < M; ++k) {
        if (bad.empty()) break; // already sorted, stop playing further rounds
        int x = J[k].first, y = J[k].second;
        if (x != y) {
            // Apply Jerry's swap
            int vx = S[x], vy = S[y];
            swap(S[x], S[y]);
            pos[vx] = y;
            pos[vy] = x;
            updateBad(x);
            updateBad(y);
        }
        // After Jerry's move, if array is sorted, do a dummy swap to keep it sorted
        if (bad.empty()) {
            int u = 0, v = 0;
            moves.push_back({u, v});
            // sumDist += 0
            continue;
        }
        int u = -1, v = -1;
        bool done = false;
        if (x != y) {
            if (S[x] != x && S[y] != y && pos[x] == y && pos[y] == x) {
                // swapping x and y fixes both
                u = x; v = y; done = true;
            }
        }
        if (!done) {
            if (x != y && S[x] != x) {
                u = x; v = pos[x]; done = true;
            } else if (x != y && S[y] != y) {
                u = y; v = pos[y]; done = true;
            } else {
                // pick any mismatched index
                int i = *bad.begin();
                u = i; v = pos[i];
            }
        }
        if (u == v) {
            // shouldn't happen for mismatched index, but safeguard
            moves.push_back({u, v});
            // sumDist += 0
            continue;
        }
        // perform our swap
        int vu = S[u], vv = S[v];
        swap(S[u], S[v]);
        pos[vu] = v;
        pos[vv] = u;
        updateBad(u);
        updateBad(v);
        moves.push_back({u, v});
        sumDist += llabs((long long)u - (long long)v);
    }
    
    int R = (int)moves.size();
    // If still not sorted after using up to M rounds, we did not find a solution
    // Remainder: rely on problem guarantee that sorting is possible within M rounds.
    // Output
    cout << R << "\n";
    for (auto &p : moves) {
        cout << p.first << " " << p.second << "\n";
    }
    long long V = (long long)R * sumDist;
    cout << V << "\n";
    return 0;
}