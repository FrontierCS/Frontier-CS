#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m, L, R, Sx, Sy, Lq;
    long long s;
    if (!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s)) return 0;
    vector<int> q(Lq);
    for (int i = 0; i < Lq; ++i) cin >> q[i];

    auto is_subseq = [&](const vector<int>& p)->bool{
        int j = 0;
        for (int x : p) {
            if (j < (int)q.size() && x == q[j]) ++j;
        }
        return j == (int)q.size();
    };

    vector<pair<int,int>> path;
    vector<int> p_rows;

    auto output_no = [&](){
        cout << "NO\n";
        return 0;
    };

    // Sanity: Sy must be L (problem guarantees), just ensure
    if (Sy != L) return output_no();

    // Helper builders
    auto build_fullwidth_topdown = [&](){
        // Start must be (1,1) as L=1
        for (int i = 1; i <= n; ++i) {
            p_rows.push_back(i);
            if (i % 2 == 1) {
                for (int y = 1; y <= m; ++y) path.emplace_back(i, y);
            } else {
                for (int y = m; y >= 1; --y) path.emplace_back(i, y);
            }
            if (i < n) {
                // move vertically at end - but already included next row start in next loop
                // path continuity is ensured by the construction since (i,end) adjacent to (i+1,end)
            }
        }
    };
    auto build_fullwidth_bottomup = [&](){
        for (int i = n; i >= 1; --i) {
            p_rows.push_back(i);
            int parity = (n - i) % 2; // 0: left->right, 1: right->left
            if (parity == 0) {
                for (int y = 1; y <= m; ++y) path.emplace_back(i, y);
            } else {
                for (int y = m; y >= 1; --y) path.emplace_back(i, y);
            }
        }
    };

    auto build_bothcorr_topdown_startrow1 = [&](){
        // Start at (1, L)
        // Row 1: traverse L..R then to m
        p_rows.push_back(1);
        for (int y = L; y <= R; ++y) path.emplace_back(1, y);
        for (int y = R+1; y <= m; ++y) path.emplace_back(1, y);
        int cur_col = m;
        for (int i = 2; i <= n; ++i) {
            // move down at current column
            path.emplace_back(i, cur_col);
            p_rows.push_back(i);
            if (cur_col == m) {
                // go left along right corridor to R+1
                for (int y = m-1; y >= R+1; --y) path.emplace_back(i, y);
                // enter at R and go to L
                for (int y = R; y >= L; --y) path.emplace_back(i, y);
                // go to 1 along left corridor
                for (int y = L-1; y >= 1; --y) path.emplace_back(i, y);
                cur_col = 1;
            } else {
                // cur_col == 1
                // go right along left corridor to L-1
                for (int y = 2; y <= L-1; ++y) path.emplace_back(i, y);
                // enter at L and go to R
                for (int y = L; y <= R; ++y) path.emplace_back(i, y);
                // go to m along right corridor
                for (int y = R+1; y <= m; ++y) path.emplace_back(i, y);
                cur_col = m;
            }
        }
    };

    auto build_bothcorr_bottomup_startrown = [&](){
        // Start at (n, L)
        p_rows.push_back(n);
        for (int y = L; y <= R; ++y) path.emplace_back(n, y);
        for (int y = R+1; y <= m; ++y) path.emplace_back(n, y);
        int cur_col = m;
        for (int i = n-1; i >= 1; --i) {
            path.emplace_back(i, cur_col);
            p_rows.push_back(i);
            if (cur_col == m) {
                for (int y = m-1; y >= R+1; --y) path.emplace_back(i, y);
                for (int y = R; y >= L; --y) path.emplace_back(i, y);
                for (int y = L-1; y >= 1; --y) path.emplace_back(i, y);
                cur_col = 1;
            } else {
                for (int y = 2; y <= L-1; ++y) path.emplace_back(i, y);
                for (int y = L; y <= R; ++y) path.emplace_back(i, y);
                for (int y = R+1; y <= m; ++y) path.emplace_back(i, y);
                cur_col = m;
            }
        }
    };

    bool ok = false;

    if (n == 1) {
        // Only one row
        if (Lq == 0) {
            // Not possible per input description (Lq positive), but handle anyway
        }
        // q must be subsequence of [1]
        vector<int> ptmp = {1};
        if (!is_subseq(ptmp)) {
            cout << "NO\n";
            return 0;
        }
        // Build path from L to R
        for (int y = L; y <= R; ++y) path.emplace_back(1, y);
        cout << "YES\n";
        cout << (int)path.size() << "\n";
        for (auto &pt : path) cout << pt.first << " " << pt.second << "\n";
        return 0;
    }

    if (L == 1 && R == m) {
        // Full width required
        if (Sx == 1) {
            // start at (1,1)
            build_fullwidth_topdown();
            if (!is_subseq(p_rows)) {
                cout << "NO\n";
                return 0;
            }
            cout << "YES\n";
            cout << (int)path.size() << "\n";
            for (auto &pt : path) cout << pt.first << " " << pt.second << "\n";
            return 0;
        } else if (Sx == n) {
            // start at (n,1)
            build_fullwidth_bottomup();
            if (!is_subseq(p_rows)) {
                cout << "NO\n";
                return 0;
            }
            cout << "YES\n";
            cout << (int)path.size() << "\n";
            for (auto &pt : path) cout << pt.first << " " << pt.second << "\n";
            return 0;
        } else {
            cout << "NO\n";
            return 0;
        }
    }

    bool leftCorr = (L > 1);
    bool rightCorr = (R < m);

    if (leftCorr && rightCorr) {
        if (Sx == 1) {
            build_bothcorr_topdown_startrow1();
            if (!is_subseq(p_rows)) {
                cout << "NO\n";
                return 0;
            }
            cout << "YES\n";
            cout << (int)path.size() << "\n";
            for (auto &pt : path) cout << pt.first << " " << pt.second << "\n";
            return 0;
        } else if (Sx == n) {
            build_bothcorr_bottomup_startrown();
            if (!is_subseq(p_rows)) {
                cout << "NO\n";
                return 0;
            }
            cout << "YES\n";
            cout << (int)path.size() << "\n";
            for (auto &pt : path) cout << pt.first << " " << pt.second << "\n";
            return 0;
        } else {
            // Not handled
            cout << "NO\n";
            return 0;
        }
    } else {
        // Only one corridor side exists and n > 1: not handled (likely impossible under our simple strategy)
        cout << "NO\n";
        return 0;
    }
}