#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        int L = (n - 3) / 2;
        vector<int> candidates;
        for (int i = 0; i < n && (int)candidates.size() < 2; ++i) {
            int cnt = 0;
            while (cnt < L) {
                cout << 0 << " " << i << endl;
                cout.flush();
                int x;
                if(!(cin >> x)) return 0;
                if (x == 0) break;
                cnt++;
            }
            if (cnt == L) {
                candidates.push_back(i);
            }
        }
        if ((int)candidates.size() < 2) {
            // Fallback: if somehow less than 2 candidates (shouldn't happen), pick any two remaining pens
            // by probing sequentially to L and adding as needed.
            for (int i = 0; i < n && (int)candidates.size() < 2; ++i) {
                bool already = false;
                for (int v : candidates) if (v == i) { already = true; break; }
                if (already) continue;
                int cnt = 0;
                while (cnt < L) {
                    cout << 0 << " " << i << endl;
                    cout.flush();
                    int x;
                    if(!(cin >> x)) return 0;
                    if (x == 0) break;
                    cnt++;
                }
                if (cnt == L) {
                    candidates.push_back(i);
                }
            }
            // As a last resort (extremely unlikely), if still not enough, just select any two distinct indices.
            if ((int)candidates.size() < 2) {
                vector<int> rem;
                vector<int> mark(n, 0);
                for (int v : candidates) mark[v] = 1;
                for (int i = 0; i < n; ++i) if (!mark[i]) rem.push_back(i);
                while ((int)candidates.size() < 2 && !rem.empty()) {
                    candidates.push_back(rem.back());
                    rem.pop_back();
                }
            }
        }
        if ((int)candidates.size() < 2) {
            // If still not possible, just pick (0,1)
            cout << 1 << " " << 0 << " " << 1 << endl;
            cout.flush();
        } else {
            cout << 1 << " " << candidates[0] << " " << candidates[1] << endl;
            cout.flush();
        }
    }
    return 0;
}