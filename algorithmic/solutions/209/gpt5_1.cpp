#include <bits/stdc++.h>
using namespace std;

using int64 = long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int h;
    if (!(cin >> h)) return 0;
    int H = h - 1;
    int n = (1 << h) - 1;
    
    auto query = [&](int u, int64 d) -> int64 {
        cout << "? " << u << " " << d << "\n";
        cout.flush();
        int64 ans;
        if (!(cin >> ans)) exit(0);
        return ans;
    };
    
    // Step 1: Find root and its two children using distances H+2 (zeros) and H+1
    vector<int> cand;
    cand.reserve(3);
    for (int u = 1; u <= n; ++u) {
        int64 ans = query(u, H + 2);
        if (ans == 0) cand.push_back(u);
    }
    int rootU = -1;
    vector<int> children;
    for (int u : cand) {
        int64 ans = query(u, H + 1);
        if (ans == 0) rootU = u;
        else children.push_back(u);
    }
    if (rootU == -1 || (int)children.size() != 2) {
        // Fallback (should not happen in correct interaction)
        // Attempt to find root by scanning H+1 for all u
        for (int u = 1; u <= n; ++u) {
            int64 ans = query(u, H + 1);
            if (ans == 0) { rootU = u; break; }
        }
        // Find children by scanning H+2 (excluding root)
        children.clear();
        for (int u = 1; u <= n && (int)children.size() < 2; ++u) {
            if (u == rootU) continue;
            int64 ans = query(u, H + 2);
            if (ans == 0) children.push_back(u);
        }
        if (rootU == -1 || (int)children.size() != 2) {
            // Give up if still inconsistent
            cout << "! 0\n";
            cout.flush();
            return 0;
        }
    }
    int c1 = children[0], c2 = children[1];
    
    // Step 2: Root queries
    int64 s1 = query(rootU, 1); // sum of children weights
    int64 s2 = query(rootU, 2); // sum at distance 2 from root
    
    // Step 3: Children queries
    int64 a1 = 0, a2 = 0; // distance 1 from children
    if (H >= 1) {
        a1 = query(c1, 1);
        a2 = query(c2, 1);
    }
    vector<int64> sumChild(H + 1, 0); // sumChild[s] = S_c1[s] + S_c2[s] for s>=0
    // Note: we only need s from 2..H-1 for recurrence
    for (int s = 2; s <= H - 1; ++s) {
        int64 q1 = query(c1, s);
        int64 q2 = query(c2, s);
        sumChild[s] = q1 + q2;
    }
    
    // Step 4: Compute f_root
    int64 f_root = (a1 + a2 - s2) / 2;
    
    // Step 5: Reconstruct S_root[k] for k=1..H
    vector<int64> Sroot(H + 1, 0); // Sroot[k] = sum at distance k from root
    if (H >= 1) Sroot[1] = s1;
    if (H >= 2) Sroot[2] = s2;
    for (int k = 3; k <= H; ++k) {
        // Sroot[k] = (S_c1[k-1] + S_c2[k-1]) - Sroot[k-2]
        Sroot[k] = sumChild[k - 1] - Sroot[k - 2];
    }
    
    // Step 6: Total sum
    int64 S = f_root;
    for (int k = 1; k <= H; ++k) S += Sroot[k];
    
    cout << "! " << S << "\n";
    cout.flush();
    return 0;
}