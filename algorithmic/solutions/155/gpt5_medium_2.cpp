#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int si, sj, ti, tj;
    double p;
    if (!(cin >> si >> sj >> ti >> tj >> p)) return 0;
    vector<string> h(20);
    for (int i = 0; i < 20; i++) cin >> h[i];
    vector<string> v(19);
    for (int i = 0; i < 19; i++) cin >> v[i];

    auto can_move = [&](int i, int j, int dir)->bool{
        // 0:U,1:D,2:L,3:R
        if (dir == 0) {
            if (i == 0) return false;
            return v[i-1][j] == '0';
        } else if (dir == 1) {
            if (i == 19) return false;
            return v[i][j] == '0';
        } else if (dir == 2) {
            if (j == 0) return false;
            return h[i][j-1] == '0';
        } else {
            if (j == 19) return false;
            return h[i][j] == '0';
        }
    };
    auto move_to = [&](int i, int j, int dir)->pair<int,int>{
        if (dir == 0) return {i-1, j};
        if (dir == 1) return {i+1, j};
        if (dir == 2) return {i, j-1};
        return {i, j+1};
    };

    const int N = 20;
    const int SZ = N*N;
    vector<int> dist(SZ, -1), prevv(SZ, -1), prevd(SZ, -1);
    queue<int> q;
    int s_id = si*20 + sj;
    int t_id = ti*20 + tj;
    dist[s_id] = 0;
    q.push(s_id);

    while (!q.empty()) {
        int u = q.front(); q.pop();
        int ui = u / 20, uj = u % 20;
        for (int d = 0; d < 4; d++) {
            if (!can_move(ui, uj, d)) continue;
            auto [vi, vj] = move_to(ui, uj, d);
            int v_id = vi*20 + vj;
            if (dist[v_id] == -1) {
                dist[v_id] = dist[u] + 1;
                prevv[v_id] = u;
                prevd[v_id] = d;
                q.push(v_id);
            }
        }
    }

    string ans;
    if (dist[t_id] != -1) {
        int cur = t_id;
        while (cur != s_id) {
            int d = prevd[cur];
            char c = 'U';
            if (d == 0) c = 'U';
            else if (d == 1) c = 'D';
            else if (d == 2) c = 'L';
            else if (d == 3) c = 'R';
            ans.push_back(c);
            cur = prevv[cur];
        }
        reverse(ans.begin(), ans.end());
    } else {
        ans = "";
    }

    if ((int)ans.size() > 200) ans = ans.substr(0, 200);
    cout << ans << "\n";

    return 0;
}