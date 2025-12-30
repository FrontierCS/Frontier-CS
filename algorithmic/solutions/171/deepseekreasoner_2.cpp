#include <bits/stdc++.h>
using namespace std;

int N;

void apply_slide(int &x, int &y, char dir) {
    if (dir == 'U') x = 0;
    else if (dir == 'D') x = N-1;
    else if (dir == 'L') y = 0;
    else if (dir == 'R') y = N-1;
}

vector<pair<char,char>> best_sequence(int x, int y, int tx, int ty) {
    int best = abs(x-tx) + abs(y-ty);
    vector<pair<char,char>> best_seq;
    // moves only
    vector<pair<char,char>> seq;
    char vdir = (tx > x ? 'D' : 'U');
    char hdir = (ty > y ? 'R' : 'L');
    for (int i = 0; i < abs(x-tx); i++) seq.push_back({'M', vdir});
    for (int i = 0; i < abs(y-ty); i++) seq.push_back({'M', hdir});
    best_seq = seq;
    
    vector<char> dirs = {'U','D','L','R'};
    // length 1
    for (char d1 : dirs) {
        int nx = x, ny = y;
        apply_slide(nx, ny, d1);
        int moves = abs(nx-tx) + abs(ny-ty);
        int total = 1 + moves;
        if (total < best) {
            best = total;
            seq.clear();
            seq.push_back({'S', d1});
            vdir = (tx > nx ? 'D' : 'U');
            hdir = (ty > ny ? 'R' : 'L');
            for (int i = 0; i < abs(nx-tx); i++) seq.push_back({'M', vdir});
            for (int i = 0; i < abs(ny-ty); i++) seq.push_back({'M', hdir});
            best_seq = seq;
        }
    }
    // length 2
    for (char d1 : dirs) {
        for (char d2 : dirs) {
            int nx = x, ny = y;
            apply_slide(nx, ny, d1);
            apply_slide(nx, ny, d2);
            int moves = abs(nx-tx) + abs(ny-ty);
            int total = 2 + moves;
            if (total < best) {
                best = total;
                seq.clear();
                seq.push_back({'S', d1});
                seq.push_back({'S', d2});
                vdir = (tx > nx ? 'D' : 'U');
                hdir = (ty > ny ? 'R' : 'L');
                for (int i = 0; i < abs(nx-tx); i++) seq.push_back({'M', vdir});
                for (int i = 0; i < abs(ny-ty); i++) seq.push_back({'M', hdir});
                best_seq = seq;
            }
        }
    }
    // length 3
    for (char d1 : dirs) {
        for (char d2 : dirs) {
            for (char d3 : dirs) {
                int nx = x, ny = y;
                apply_slide(nx, ny, d1);
                apply_slide(nx, ny, d2);
                apply_slide(nx, ny, d3);
                int moves = abs(nx-tx) + abs(ny-ty);
                int total = 3 + moves;
                if (total < best) {
                    best = total;
                    seq.clear();
                    seq.push_back({'S', d1});
                    seq.push_back({'S', d2});
                    seq.push_back({'S', d3});
                    vdir = (tx > nx ? 'D' : 'U');
                    hdir = (ty > ny ? 'R' : 'L');
                    for (int i = 0; i < abs(nx-tx); i++) seq.push_back({'M', vdir});
                    for (int i = 0; i < abs(ny-ty); i++) seq.push_back({'M', hdir});
                    best_seq = seq;
                }
            }
        }
    }
    return best_seq;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int M;
    cin >> N >> M;
    vector<int> xs(M), ys(M);
    for (int i = 0; i < M; i++) {
        cin >> xs[i] >> ys[i];
    }
    int cur_x = xs[0], cur_y = ys[0];
    vector<pair<char,char>> actions;
    for (int i = 1; i < M; i++) {
        int tx = xs[i], ty = ys[i];
        vector<pair<char,char>> seq = best_sequence(cur_x, cur_y, tx, ty);
        actions.insert(actions.end(), seq.begin(), seq.end());
        cur_x = tx;
        cur_y = ty;
    }
    for (auto &act : actions) {
        cout << act.first << " " << act.second << "\n";
    }
    return 0;
}