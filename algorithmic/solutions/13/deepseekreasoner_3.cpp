#include <iostream>
#include <vector>
#include <utility>

using namespace std;

bool black[22][22]; // 1-indexed, up to 21

int main() {
    int sx, sy;
    cin >> sx >> sy;
    int rx = sx, ry = sy;

    // Phase 1: build fence around 20x20 region
    // Fence cells: (21, y) for y=1..20 and (x, 21) for x=1..20
    vector<pair<int, int>> fenceCells;
    for (int y = 1; y <= 20; y++) fenceCells.push_back({21, y});
    for (int x = 1; x <= 20; x++) fenceCells.push_back({x, 21});
    int fenceMarked = 0;
    int fenceIdx = 0;

    while (fenceMarked < 40) {
        int nx, ny;
        if (rx == 20 && !black[21][ry]) {
            nx = 21; ny = ry;
        } else if (ry == 20 && !black[rx][21]) {
            nx = rx; ny = 21;
        } else {
            // pick next unmarked fence cell
            while (fenceIdx < 40 && black[fenceCells[fenceIdx].first][fenceCells[fenceIdx].second]) {
                fenceIdx++;
            }
            if (fenceIdx < 40) {
                nx = fenceCells[fenceIdx].first;
                ny = fenceCells[fenceIdx].second;
            } else {
                // should not happen
                break;
            }
        }

        cout << nx << " " << ny << endl;
        cout.flush();

        if (!black[nx][ny]) {
            black[nx][ny] = true;
            fenceMarked++;
        }

        int ax, ay;
        cin >> ax >> ay;
        if (ax == 0 && ay == 0) {
            return 0;
        }
        rx = ax; ry = ay;
    }

    // Phase 2: fill interior 1..20 x 1..20
    for (int x = 1; x <= 20; x++) {
        for (int y = 1; y <= 20; y++) {
            if (!black[x][y]) {
                cout << x << " " << y << endl;
                cout.flush();
                black[x][y] = true;

                int ax, ay;
                cin >> ax >> ay;
                if (ax == 0 && ay == 0) {
                    return 0;
                }
                rx = ax; ry = ay;
            }
        }
    }

    // If we reach here, the robot should have exploded already.
    return 0;
}