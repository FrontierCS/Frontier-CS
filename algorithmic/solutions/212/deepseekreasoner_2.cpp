#include <iostream>
#include <vector>
#include <queue>
#include <unordered_set>
#include <algorithm>
#include <cstring>
using namespace std;

struct Point {
    int r, c;
};

// BFS to find shortest path from (sr,sc) to (tr,tc) avoiding visited cells and
// required cells of blocked rows (except the target cell).
vector<Point> bfs(int sr, int sc, int tr, int tc,
                  const unordered_set<int>& blocked,
                  const vector<vector<bool>>& visited,
                  int n, int m, int L, int R) {
    // Direction vectors: up, down, left, right
    const int dr[4] = {-1, 1, 0, 0};
    const int dc[4] = {0, 0, -1, 1};

    vector<vector<Point>> parent(n+1, vector<Point>(m+1, {-1,-1}));
    vector<vector<bool>> inq(n+1, vector<bool>(m+1, false));
    queue<Point> q;
    q.push({sr, sc});
    inq[sr][sc] = true;

    while (!q.empty()) {
        Point cur = q.front(); q.pop();
        if (cur.r == tr && cur.c == tc) break;
        for (int d = 0; d < 4; d++) {
            int nr = cur.r + dr[d];
            int nc = cur.c + dc[d];
            if (nr < 1 || nr > n || nc < 1 || nc > m) continue;
            if (inq[nr][nc]) continue;
            if (visited[nr][nc]) continue;
            // Check if this cell is a required cell of a blocked row
            if (L <= nc && nc <= R) {
                if (nr == tr && nc == tc) {
                    // target is allowed
                } else if (blocked.count(nr)) {
                    continue;
                }
            }
            parent[nr][nc] = cur;
            inq[nr][nc] = true;
            q.push({nr, nc});
        }
    }

    if (!inq[tr][tc]) {
        return {}; // no path
    }

    // Reconstruct path from target to start
    vector<Point> path;
    Point cur = {tr, tc};
    while (cur.r != -1) {
        path.push_back(cur);
        cur = parent[cur.r][cur.c];
    }
    reverse(path.begin(), path.end());
    // Remove the starting cell (sr,sc) from the path
    path.erase(path.begin());
    return path;
}

// Check if q is a subsequence of p
bool is_subseq(const vector<int>& p, const vector<int>& q) {
    int j = 0;
    for (int x : p) {
        if (j < (int)q.size() && x == q[j]) j++;
    }
    return j == (int)q.size();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n, m, L, R, Sx, Sy, Lq, s;
    cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s;
    vector<int> q(Lq);
    for (int i = 0; i < Lq; i++) cin >> q[i];

    // Check necessary condition
    auto it = find(q.begin(), q.end(), Sx);
    if (it != q.end() && q[0] != Sx) {
        cout << "NO\n";
        return 0;
    }

    // Generate candidate permutations p
    vector<vector<int>> candidates;

    // Candidate 1: increasing from Sx to n, then 1 to Sx-1
    vector<int> p1;
    for (int r = Sx; r <= n; r++) p1.push_back(r);
    for (int r = 1; r < Sx; r++) p1.push_back(r);
    if (is_subseq(p1, q)) candidates.push_back(p1);

    // Candidate 2: decreasing from Sx to 1, then n to Sx+1
    vector<int> p2;
    for (int r = Sx; r >= 1; r--) p2.push_back(r);
    for (int r = n; r > Sx; r--) p2.push_back(r);
    if (is_subseq(p2, q)) candidates.push_back(p2);

    // Candidate 3: Sx, then rows not in q (increasing), then q (with Sx removed if present)
    vector<int> p3;
    p3.push_back(Sx);
    vector<int> notq;
    for (int r = 1; r <= n; r++) {
        if (r != Sx && find(q.begin(), q.end(), r) == q.end())
            notq.push_back(r);
    }
    sort(notq.begin(), notq.end());
    p3.insert(p3.end(), notq.begin(), notq.end());
    vector<int> qcopy = q;
    if (find(qcopy.begin(), qcopy.end(), Sx) != qcopy.end()) {
        qcopy.erase(qcopy.begin());
    }
    p3.insert(p3.end(), qcopy.begin(), qcopy.end());
    if (is_subseq(p3, q)) candidates.push_back(p3);

    // Candidate 4: same as p3 but decreasing order of notq
    vector<int> p4;
    p4.push_back(Sx);
    vector<int> notq2;
    for (int r = 1; r <= n; r++) {
        if (r != Sx && find(q.begin(), q.end(), r) == q.end())
            notq2.push_back(r);
    }
    sort(notq2.begin(), notq2.end(), greater<int>());
    p4.insert(p4.end(), notq2.begin(), notq2.end());
    p4.insert(p4.end(), qcopy.begin(), qcopy.end());
    if (is_subseq(p4, q)) candidates.push_back(p4);

    // Try each candidate
    for (const vector<int>& p : candidates) {
        vector<vector<bool>> visited(n+1, vector<bool>(m+1, false));
        vector<Point> path;

        int cur_r = Sx, cur_c = L;
        visited[cur_r][cur_c] = true;
        path.push_back({cur_r, cur_c});

        bool ok = true;
        for (int i = 0; i < n; i++) {
            int row = p[i];
            bool l2r = (i % 2 == 0); // even index -> left to right
            int start_col = l2r ? L : R;
            int end_col   = l2r ? R : L;

            if (i > 0) {
                // Connect from (cur_r, cur_c) to (row, start_col)
                unordered_set<int> blocked_rows;
                for (int j = i; j < n; j++) blocked_rows.insert(p[j]);

                vector<Point> conn = bfs(cur_r, cur_c, row, start_col,
                                         blocked_rows, visited,
                                         n, m, L, R);
                if (conn.empty()) {
                    ok = false;
                    break;
                }
                for (const Point& pt : conn) {
                    path.push_back(pt);
                    visited[pt.r][pt.c] = true;
                }
                cur_r = row;
                cur_c = start_col;
            }

            // Traverse the required cells of this row
            // We are already at start_col, need to cover all required columns
            vector<int> cols;
            if (l2r) {
                for (int c = L; c <= R; c++) cols.push_back(c);
            } else {
                for (int c = R; c >= L; c--) cols.push_back(c);
            }
            // Find the position of start_col in cols
            int pos = 0;
            while (pos < (int)cols.size() && cols[pos] != start_col) pos++;
            // Traverse from the next column onwards
            for (int j = pos+1; j < (int)cols.size(); j++) {
                int c = cols[j];
                if (visited[row][c]) {
                    ok = false;
                    break;
                }
                path.push_back({row, c});
                visited[row][c] = true;
                cur_r = row;
                cur_c = c;
            }
            if (!ok) break;
        }

        // Verify that all required cells are visited
        if (ok) {
            for (int r = 1; r <= n; r++) {
                for (int c = L; c <= R; c++) {
                    if (!visited[r][c]) {
                        ok = false;
                        break;
                    }
                }
                if (!ok) break;
            }
        }

        if (ok) {
            cout << "YES\n";
            cout << path.size() << "\n";
            for (const Point& pt : path) {
                cout << pt.r << " " << pt.c << "\n";
            }
            return 0;
        }
    }

    cout << "NO\n";
    return 0;
}