#include <bits/stdc++.h>
using namespace std;

using pii = pair<int,int>;

bool is_subseq(const vector<int>& p, const vector<int>& q){
    size_t j = 0;
    for (int x : p){
        if (j < q.size() && x == q[j]) ++j;
    }
    return j == q.size();
}

vector<pii> build_inc(int n, int m, int L, int R, int Sx){
    vector<pii> path;
    auto add = [&](int x, int y){ path.emplace_back(x,y); };
    auto go_horiz = [&](int x, int y_from, int y_to){
        if (y_from < y_to){
            for (int y = y_from + 1; y <= y_to; ++y) add(x,y);
        }else{
            for (int y = y_from - 1; y >= y_to; --y) add(x,y);
        }
    };
    auto go_vert = [&](int x_from, int x_to, int y){
        if (x_from < x_to){
            for (int x = x_from + 1; x <= x_to; ++x) add(x,y);
        }else{
            for (int x = x_from - 1; x >= x_to; --x) add(x,y);
        }
    };

    if (Sx == 1){
        int x = 1, y = L;
        add(x,y);
        go_horiz(x, y, R);
        y = R;
        for (int r = 2; r <= n; ++r){
            go_vert(x, r, y);
            x = r;
            if (y == R){
                go_horiz(x, y, L);
                y = L;
            }else{
                go_horiz(x, y, R);
                y = R;
            }
        }
        return path;
    }else{
        bool leftExist = (L > 1);
        bool rightExist = (R < m);
        if (!leftExist && !rightExist) return {}; // no corridor to escape
        int x = Sx, y = L;
        add(x,y);
        go_horiz(x, y, R);
        y = R;
        for (int r = Sx + 1; r <= n; ++r){
            go_vert(x, r, y);
            x = r;
            if (y == R){
                go_horiz(x, y, L);
                y = L;
            }else{
                go_horiz(x, y, R);
                y = R;
            }
        }
        // at (n, y). Need to step to corridor adjacent to y.
        int corridorCol = -1;
        if (y == L && leftExist) corridorCol = L - 1;
        else if (y == R && rightExist) corridorCol = R + 1;
        else return {};
        go_horiz(x, y, corridorCol);
        y = corridorCol;
        // go up corridor to row 1
        go_vert(x, 1, y);
        x = 1;
        // enter D at row 1
        int enterCol = (corridorCol == L - 1) ? L : R;
        go_horiz(x, y, enterCol);
        y = enterCol;
        // traverse rows 1..Sx-1
        if (Sx - 1 >= 1){
            if (y == L){
                go_horiz(x, y, R);
                y = R;
            }else{
                go_horiz(x, y, L);
                y = L;
            }
            for (int r = 2; r <= Sx - 1; ++r){
                go_vert(x, r, y);
                x = r;
                if (y == R){
                    go_horiz(x, y, L);
                    y = L;
                }else{
                    go_horiz(x, y, R);
                    y = R;
                }
            }
        }
        return path;
    }
}

vector<pii> build_dec(int n, int m, int L, int R, int Sx){
    vector<pii> path;
    auto add = [&](int x, int y){ path.emplace_back(x,y); };
    auto go_horiz = [&](int x, int y_from, int y_to){
        if (y_from < y_to){
            for (int y = y_from + 1; y <= y_to; ++y) add(x,y);
        }else{
            for (int y = y_from - 1; y >= y_to; --y) add(x,y);
        }
    };
    auto go_vert = [&](int x_from, int x_to, int y){
        if (x_from < x_to){
            for (int x = x_from + 1; x <= x_to; ++x) add(x,y);
        }else{
            for (int x = x_from - 1; x >= x_to; --x) add(x,y);
        }
    };

    if (Sx == n){
        int x = n, y = L;
        add(x,y);
        go_horiz(x, y, R);
        y = R;
        for (int r = n - 1; r >= 1; --r){
            go_vert(x, r, y);
            x = r;
            if (y == R){
                go_horiz(x, y, L);
                y = L;
            }else{
                go_horiz(x, y, R);
                y = R;
            }
        }
        return path;
    }else{
        bool leftExist = (L > 1);
        bool rightExist = (R < m);
        if (!leftExist && !rightExist) return {}; // no corridor to escape
        int x = Sx, y = L;
        add(x,y);
        go_horiz(x, y, R);
        y = R;
        for (int r = Sx - 1; r >= 1; --r){
            go_vert(x, r, y);
            x = r;
            if (y == R){
                go_horiz(x, y, L);
                y = L;
            }else{
                go_horiz(x, y, R);
                y = R;
            }
        }
        // at (1, y). Need to step to corridor adjacent to y.
        int corridorCol = -1;
        if (y == L && leftExist) corridorCol = L - 1;
        else if (y == R && rightExist) corridorCol = R + 1;
        else return {};
        go_horiz(x, y, corridorCol);
        y = corridorCol;
        // go down corridor to row n
        go_vert(x, n, y);
        x = n;
        // enter D at row n
        int enterCol = (corridorCol == L - 1) ? L : R;
        go_horiz(x, y, enterCol);
        y = enterCol;
        // traverse rows n..Sx+1 upwards
        if (Sx + 1 <= n){
            if (y == L){
                go_horiz(x, y, R);
                y = R;
            }else{
                go_horiz(x, y, L);
                y = L;
            }
            for (int r = n - 1; r >= Sx + 1; --r){
                go_vert(x, r, y);
                x = r;
                if (y == R){
                    go_horiz(x, y, L);
                    y = L;
                }else{
                    go_horiz(x, y, R);
                    y = R;
                }
            }
        }
        return path;
    }
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m, L, R, Sx, Sy, Lq;
    long long s_param;
    if (!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s_param)) {
        return 0;
    }
    vector<int> q(Lq);
    for (int i = 0; i < Lq; ++i) cin >> q[i];

    // Build possible p sequences
    vector<int> p_inc, p_dec;
    // Increasing rotated: Sx..n, 1..Sx-1
    for (int i = Sx; i <= n; ++i) p_inc.push_back(i);
    for (int i = 1; i <= Sx - 1; ++i) p_inc.push_back(i);
    // Decreasing rotated: Sx..1, n..Sx+1
    for (int i = Sx; i >= 1; --i) p_dec.push_back(i);
    for (int i = n; i >= Sx + 1; --i) p_dec.push_back(i);

    auto q_in_range = [&](){
        for (int v : q){
            if (v < 1 || v > n) return false;
        }
        return true;
    };

    if (!q_in_range()){
        cout << "NO\n";
        return 0;
    }

    vector<pii> ans;

    // Try increasing rotated
    if (is_subseq(p_inc, q)){
        ans = build_inc(n, m, L, R, Sx);
        if (!ans.empty()){
            cout << "YES\n";
            cout << ans.size() << "\n";
            for (auto &pt : ans) cout << pt.first << " " << pt.second << "\n";
            return 0;
        }
    }
    // Try decreasing rotated
    if (is_subseq(p_dec, q)){
        ans = build_dec(n, m, L, R, Sx);
        if (!ans.empty()){
            cout << "YES\n";
            cout << ans.size() << "\n";
            for (auto &pt : ans) cout << pt.first << " " << pt.second << "\n";
            return 0;
        }
    }

    cout << "NO\n";
    return 0;
}