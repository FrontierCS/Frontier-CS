#include <bits/stdc++.h>
using namespace std;

string readDigits(int len) {
    string ret, s;
    while ((int)ret.size() < len && (cin >> s)) ret += s;
    if ((int)ret.size() > len) ret.resize(len);
    return ret;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj, ti, tj;
    double p;
    if (!(cin >> si >> sj >> ti >> tj >> p)) {
        cout << "\n";
        return 0;
    }

    vector<string> h(20), v(19);
    for (int i = 0; i < 20; i++) h[i] = readDigits(19);
    for (int i = 0; i < 19; i++) v[i] = readDigits(20);

    const int H = 20, W = 20;
    vector<vector<int>> dist(H, vector<int>(W, -1));
    vector<vector<pair<int,int>>> parent(H, vector<pair<int,int>>(W, {-1, -1}));
    vector<vector<char>> mv(H, vector<char>(W, '?'));
    queue<pair<int,int>> q;
    q.push({si, sj});
    dist[si][sj] = 0;

    auto try_push = [&](int i, int j, int ni, int nj, char c, bool open) {
        if (!open) return;
        if (ni < 0 || ni >= H || nj < 0 || nj >= W) return;
        if (dist[ni][nj] != -1) return;
        dist[ni][nj] = dist[i][j] + 1;
        parent[ni][nj] = {i, j};
        mv[ni][nj] = c;
        q.push({ni, nj});
    };

    while (!q.empty()) {
        auto [i, j] = q.front();
        q.pop();
        if (i == ti && j == tj) break;
        if (i > 0) try_push(i, j, i - 1, j, 'U', v[i - 1][j] == '0');
        if (i < 19) try_push(i, j, i + 1, j, 'D', v[i][j] == '0');
        if (j > 0) try_push(i, j, i, j - 1, 'L', h[i][j - 1] == '0');
        if (j < 19) try_push(i, j, i, j + 1, 'R', h[i][j] == '0');
    }

    string path;
    if (dist[ti][tj] != -1) {
        int i = ti, j = tj;
        while (!(i == si && j == sj)) {
            path.push_back(mv[i][j]);
            auto pr = parent[i][j];
            i = pr.first;
            j = pr.second;
        }
        reverse(path.begin(), path.end());
    } else {
        // Fallback: naive Manhattan moves (ignoring walls)
        int i = si, j = sj;
        while (i < ti && (int)path.size() < 200) { path.push_back('D'); i++; }
        while (j < tj && (int)path.size() < 200) { path.push_back('R'); j++; }
        while (i > ti && (int)path.size() < 200) { path.push_back('U'); i--; }
        while (j > tj && (int)path.size() < 200) { path.push_back('L'); j--; }
    }

    if ((int)path.size() > 200) path.resize(200);
    cout << path << '\n';
    return 0;
}