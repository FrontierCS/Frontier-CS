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

    auto is_subseq = [&](const vector<int>& order)->bool{
        int j = 0;
        for (int x: order) {
            if (j < (int)q.size() && x == q[j]) ++j;
        }
        return j == (int)q.size();
    };

    // Build orders
    vector<int> order_down_first; // Sx..n, 1..Sx-1
    for (int r = Sx; r <= n; ++r) order_down_first.push_back(r);
    for (int r = 1; r <= Sx - 1; ++r) order_down_first.push_back(r);

    vector<int> order_up_first; // Sx..1, n..Sx+1
    for (int r = Sx; r >= 1; --r) order_up_first.push_back(r);
    for (int r = n; r >= Sx + 1; --r) order_up_first.push_back(r);

    bool corridor_left = (L > 1);
    bool corridor_right = (R < m);

    auto feasible_down_first = [&]()->bool{
        if (Sx == 1) return true; // no jump needed
        int endcol = ((n - Sx) % 2 == 0) ? R : L;
        if (endcol == R) return corridor_right;
        else return corridor_left;
    };

    auto feasible_up_first = [&]()->bool{
        if (Sx == n) return true; // no jump needed
        int endcol = ((1 - Sx) % 2 == 0) ? R : L;
        if (endcol == R) return corridor_right;
        else return corridor_left;
    };

    bool fe1 = feasible_down_first();
    bool fe2 = feasible_up_first();
    bool ok1 = fe1 && is_subseq(order_down_first);
    bool ok2 = fe2 && is_subseq(order_up_first);

    auto build_down_first = [&]()->vector<pair<int,int>>{
        vector<pair<int,int>> path;
        auto push = [&](int x,int y){ path.emplace_back(x,y); };
        // Phase 1: rows Sx..n
        // Start at (Sx, L), traverse to R
        for (int y = L; y <= R; ++y) push(Sx, y);
        int cur_col = R;
        for (int r = Sx + 1; r <= n; ++r) {
            // move down to same column
            push(r, cur_col);
            int to = (cur_col == R ? L : R);
            if (cur_col < to) {
                for (int y = cur_col + 1; y <= to; ++y) push(r, y);
            } else {
                for (int y = cur_col - 1; y >= to; --y) push(r, y);
            }
            cur_col = to;
        }
        if (Sx > 1) {
            // jump via corridor to row 1
            int endcol = cur_col; // at row n
            int c = (endcol == R ? R + 1 : L - 1);
            // step into corridor
            push(n, c);
            // move along corridor up to row 1
            for (int r = n - 1; r >= 1; --r) push(r, c);
            // step into row 1 at endcol
            push(1, endcol);
            // traverse row 1 to other end
            int to = (endcol == R ? L : R);
            if (endcol < to) {
                for (int y = endcol + 1; y <= to; ++y) push(1, y);
            } else {
                for (int y = endcol - 1; y >= to; --y) push(1, y);
            }
            cur_col = to;
            // rows 2..Sx-1
            for (int r = 2; r <= Sx - 1; ++r) {
                // step down into row r at cur_col
                push(r, cur_col);
                int to2 = (cur_col == R ? L : R);
                if (cur_col < to2) {
                    for (int y = cur_col + 1; y <= to2; ++y) push(r, y);
                } else {
                    for (int y = cur_col - 1; y >= to2; --y) push(r, y);
                }
                cur_col = to2;
            }
        }
        return path;
    };

    auto build_up_first = [&]()->vector<pair<int,int>>{
        vector<pair<int,int>> path;
        auto push = [&](int x,int y){ path.emplace_back(x,y); };
        // Start at (Sx, L), traverse to R
        for (int y = L; y <= R; ++y) push(Sx, y);
        int cur_col = R;
        // Move up to row 1
        for (int r = Sx - 1; r >= 1; --r) {
            push(r, cur_col);
            int to = (cur_col == R ? L : R);
            if (cur_col < to) {
                for (int y = cur_col + 1; y <= to; ++y) push(r, y);
            } else {
                for (int y = cur_col - 1; y >= to; --y) push(r, y);
            }
            cur_col = to;
        }
        if (Sx < n) {
            // jump via corridor to row n
            int endcol = cur_col; // at row 1
            int c = (endcol == R ? R + 1 : L - 1);
            push(1, c);
            for (int r = 2; r <= n; ++r) push(r, c);
            // step into row n at endcol
            push(n, endcol);
            int to = (endcol == R ? L : R);
            if (endcol < to) {
                for (int y = endcol + 1; y <= to; ++y) push(n, y);
            } else {
                for (int y = endcol - 1; y >= to; --y) push(n, y);
            }
            cur_col = to;
            // rows n-1 down to Sx+1
            for (int r = n - 1; r >= Sx + 1; --r) {
                push(r, cur_col);
                int to2 = (cur_col == R ? L : R);
                if (cur_col < to2) {
                    for (int y = cur_col + 1; y <= to2; ++y) push(r, y);
                } else {
                    for (int y = cur_col - 1; y >= to2; --y) push(r, y);
                }
                cur_col = to2;
            }
        }
        return path;
    };

    if (!ok1 && !ok2) {
        cout << "NO\n";
        return 0;
    }

    vector<pair<int,int>> path;
    if (ok1) {
        path = build_down_first();
    } else {
        path = build_up_first();
    }

    // Safety: ensure no duplicates and within bounds
    vector<vector<bool>> vis(n+1, vector<bool>(m+1,false));
    bool valid = true;
    for (auto &p : path) {
        int x = p.first, y = p.second;
        if (x < 1 || x > n || y < 1 || y > m) { valid = false; break; }
        if (vis[x][y]) { valid = false; break; }
        vis[x][y] = true;
    }
    // Ensure all required cells visited
    if (valid) {
        for (int x = 1; x <= n; ++x) {
            for (int y = L; y <= R; ++y) {
                if (!vis[x][y]) { valid = false; break; }
            }
            if (!valid) break;
        }
    }
    if (!valid) {
        cout << "NO\n";
        return 0;
    }

    cout << "YES\n";
    cout << (int)path.size() << "\n";
    for (auto &p : path) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}