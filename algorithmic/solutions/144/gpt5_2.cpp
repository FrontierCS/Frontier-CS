#include <bits/stdc++.h>
using namespace std;

int n, L, H;

pair<int,int> query_excluding(int a, int b) {
    vector<int> q;
    q.reserve(n-2);
    for (int i = 1; i <= n; ++i) if (i != a && i != b) q.push_back(i);
    cout << 0 << " " << q.size();
    for (int x : q) cout << " " << x;
    cout << endl;
    cout.flush();
    int m1, m2;
    if (!(cin >> m1 >> m2)) {
        // In case of input failure, terminate.
        exit(0);
    }
    return {m1, m2};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n)) return 0;
    L = n / 2;
    H = L + 1;

    int r = 1;
    vector<pair<int,int>> res(n+1, {-1,-1});
    bool found_both = false;
    bool has_both_right = false; // (L-1, L)
    bool has_L_and_right = false; // (L-1, H)
    int idxL = -1, idxH = -1;

    // Scan all i against r
    for (int i = 1; i <= n; ++i) {
        if (i == r) continue;
        auto pr = query_excluding(r, i);
        res[i] = pr;
        int a = pr.first, b = pr.second;

        if (a == L-1 && b == L+2) {
            // r and i are the medians (L and H)
            cout << 1 << " " << r << " " << i << endl;
            cout.flush();
            return 0;
        }
        if (a == L-1 && b == L) has_both_right = true;
        if (a == L-1 && b == H) has_L_and_right = true;
    }

    // Classify r
    // If has_both_right -> r is RIGHT (>= H)
    // else if has_L_and_right -> r is L
    // else -> r is LOW (< L)
    if (has_both_right) {
        // r is RIGHT (>= H)
        bool r_is_H = false;
        int low_example = -1;

        // Check if there exists i such that (L, L+2), which happens iff one is H and the other low.
        for (int i = 1; i <= n; ++i) if (i != r) {
            auto pr = res[i];
            if (pr.first == L && pr.second == L+2) {
                r_is_H = true;
                low_example = i;
                break;
            }
        }

        if (r_is_H) {
            // r is H, find idxL using (L-1, H) with i = L
            for (int i = 1; i <= n; ++i) if (i != r) {
                auto pr = res[i];
                if (pr.first == L-1 && pr.second == H) {
                    idxL = i;
                    break;
                }
            }
            idxH = r;
            cout << 1 << " " << idxL << " " << idxH << endl;
            cout.flush();
            return 0;
        } else {
            // r > H
            // Find idxL via (L-1, H)
            for (int i = 1; i <= n; ++i) if (i != r) {
                auto pr = res[i];
                if (pr.first == L-1 && pr.second == H) {
                    idxL = i;
                    break;
                }
            }
            // Now find idxH by testing exclude {idxL, s} and looking for (L-1, L+2)
            for (int s = 1; s <= n; ++s) if (s != idxL) {
                auto pr2 = query_excluding(idxL, s);
                if (pr2.first == L-1 && pr2.second == L+2) {
                    idxH = s;
                    break;
                }
            }
            cout << 1 << " " << idxL << " " << idxH << endl;
            cout.flush();
            return 0;
        }
    } else if (has_L_and_right) {
        // r is L (since no both-right pairs)
        // We should have found the 'both medians' case earlier when paired with H, but handle robustly:
        // Find H by scanning pairs with r to locate (L-1, L+2)
        for (int i = 1; i <= n; ++i) if (i != r) {
            auto pr = res[i];
            if (pr.first == L-1 && pr.second == L+2) {
                idxH = i;
                break;
            }
        }
        idxL = r;
        cout << 1 << " " << idxL << " " << idxH << endl;
        cout.flush();
        return 0;
    } else {
        // r is LOW
        // Find idxH via (L, L+2)
        for (int i = 1; i <= n; ++i) if (i != r) {
            auto pr = res[i];
            if (pr.first == L && pr.second == L+2) {
                idxH = i;
                break;
            }
        }
        // Among those with (H, L+2), one is L, others are LOW.
        // Test candidates that produced (H, L+2) with idxH to find L via (L-1, L+2)
        vector<int> cand;
        for (int i = 1; i <= n; ++i) if (i != r) {
            auto pr = res[i];
            if (pr.first == H && pr.second == L+2) cand.push_back(i);
        }
        for (int s : cand) {
            auto pr2 = query_excluding(idxH, s);
            if (pr2.first == L-1 && pr2.second == L+2) {
                idxL = s;
                break;
            }
        }
        cout << 1 << " " << idxL << " " << idxH << endl;
        cout.flush();
        return 0;
    }
}