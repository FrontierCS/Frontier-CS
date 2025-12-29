#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    
    long double sN = sqrtl((long double)n);
    long double sM = sqrtl((long double)m);
    long double cand1 = (long double)n * sM + (long double)m;
    long double cand2 = (long double)m * sN + (long double)n;
    
    vector<pair<int,int>> edges;
    
    if (cand1 <= cand2) {
        // Row-centric: ensure each row picks up to floor(sqrt(m)) columns
        int D = max(1, (int)floor(sM));
        vector<vector<int>> forb(m + 1);
        vector<int> ban(m + 1, 0), inRow(m + 1, 0);
        int stamp = 1, rowStamp = 1;
        
        for (int r = 1; r <= n; ++r) {
            ++stamp;
            ++rowStamp;
            vector<int> cur;
            int start = (int)(((long long)(r - 1) * 239017LL) % m);
            for (int it = 0; it < m && (int)cur.size() < D; ++it) {
                int c = 1 + (start + it) % m;
                if (inRow[c] == rowStamp) continue;
                if (ban[c] == stamp) continue;
                // select c
                cur.push_back(c);
                inRow[c] = rowStamp;
                // mark bans from previous pairs 
                for (int x : forb[c]) ban[x] = stamp;
            }
            // update forb with all pairs in cur
            int sz = (int)cur.size();
            for (int i = 0; i < sz; ++i) {
                for (int j = i + 1; j < sz; ++j) {
                    int a = cur[i], b = cur[j];
                    forb[a].push_back(b);
                    forb[b].push_back(a);
                }
                edges.emplace_back(r, cur[i]);
            }
        }
    } else {
        // Column-centric: ensure each column picks up to floor(sqrt(n)) rows
        int D = max(1, (int)floor(sN));
        vector<vector<int>> forb(n + 1);
        vector<int> ban(n + 1, 0), inCol(n + 1, 0);
        int stamp = 1, colStamp = 1;
        
        for (int c = 1; c <= m; ++c) {
            ++stamp;
            ++colStamp;
            vector<int> cur;
            int start = (int)(((long long)(c - 1) * 239017LL) % n);
            for (int it = 0; it < n && (int)cur.size() < D; ++it) {
                int r = 1 + (start + it) % n;
                if (inCol[r] == colStamp) continue;
                if (ban[r] == stamp) continue;
                // select r
                cur.push_back(r);
                inCol[r] = colStamp;
                for (int x : forb[r]) ban[x] = stamp;
            }
            // update forb with all pairs in cur
            int sz = (int)cur.size();
            for (int i = 0; i < sz; ++i) {
                for (int j = i + 1; j < sz; ++j) {
                    int a = cur[i], b = cur[j];
                    forb[a].push_back(b);
                    forb[b].push_back(a);
                }
                edges.emplace_back(cur[i], c);
            }
        }
    }
    
    cout << edges.size() << '\n';
    for (auto &e : edges) {
        cout << e.first << ' ' << e.second << '\n';
    }
    return 0;
}