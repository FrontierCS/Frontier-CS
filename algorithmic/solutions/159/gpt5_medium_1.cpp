#include <bits/stdc++.h>
using namespace std;

struct Op {
    int x1,y1,x2,y2,x3,y3,x4,y4;
};

int N, M;
vector<vector<char>> initDot;

vector<Op> simulate(int parity) {
    vector<vector<char>> hasDot = initDot;
    vector<Op> ops;
    queue<pair<int,int>> q;

    auto push_if_candidate = [&](int x, int y){
        if (x < 0 || y < 0 || x >= N-1 || y >= N-1) return;
        if (((x + y) & 1) != parity) return;
        // corners in CCW: bl, br, tr, tl
        int cx[4] = {x, x+1, x+1, x};
        int cy[4] = {y, y, y+1, y+1};
        int cnt = 0, miss = -1;
        for (int i = 0; i < 4; ++i) {
            if (hasDot[cx[i]][cy[i]]) cnt++;
            else miss = i;
        }
        if (cnt == 3) q.emplace(x,y);
    };

    for (int x = 0; x < N-1; ++x) {
        for (int y = 0; y < N-1; ++y) {
            if (((x + y) & 1) != parity) continue;
            push_if_candidate(x,y);
        }
    }

    while (!q.empty()) {
        auto [x,y] = q.front(); q.pop();
        if (x < 0 || y < 0 || x >= N-1 || y >= N-1) continue;
        if (((x + y) & 1) != parity) continue;

        int cx[4] = {x, x+1, x+1, x};
        int cy[4] = {y, y, y+1, y+1};
        int cnt = 0, miss = -1;
        for (int i = 0; i < 4; ++i) {
            if (hasDot[cx[i]][cy[i]]) cnt++;
            else miss = i;
        }
        if (cnt != 3) continue;
        // Place new dot at missing corner
        int x1 = cx[miss], y1 = cy[miss];
        if (hasDot[x1][y1]) continue; // should not happen, but safety

        int x2 = cx[(miss+1)&3], y2 = cy[(miss+1)&3];
        int x3 = cx[(miss+2)&3], y3 = cy[(miss+2)&3];
        int x4 = cx[(miss+3)&3], y4 = cy[(miss+3)&3];

        // All three should be dots
        if (!(hasDot[x2][y2] && hasDot[x3][y3] && hasDot[x4][y4])) continue;

        hasDot[x1][y1] = 1;
        ops.push_back({x1,y1,x2,y2,x3,y3,x4,y4});

        // Update neighboring cells that include (x1,y1) as a corner
        for (int dx = -1; dx <= 0; ++dx) {
            for (int dy = -1; dy <= 0; ++dy) {
                int nx = x1 + dx;
                int ny = y1 + dy;
                push_if_candidate(nx, ny);
            }
        }
    }

    return ops;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N >> M)) {
        return 0;
    }
    initDot.assign(N, vector<char>(N, 0));
    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        if (0 <= x && x < N && 0 <= y && y < N)
            initDot[x][y] = 1;
    }

    vector<Op> ops0 = simulate(0);
    vector<Op> ops1 = simulate(1);

    vector<Op> best = (ops0.size() >= ops1.size()) ? ops0 : ops1;

    cout << best.size() << "\n";
    for (auto &op : best) {
        cout << op.x1 << ' ' << op.y1 << ' '
             << op.x2 << ' ' << op.y2 << ' '
             << op.x3 << ' ' << op.y3 << ' '
             << op.x4 << ' ' << op.y4 << '\n';
    }

    return 0;
}