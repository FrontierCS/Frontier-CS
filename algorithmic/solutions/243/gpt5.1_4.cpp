#include <bits/stdc++.h>
using namespace std;

const int MAXR = 105;
const int MAXC = 105;
const int MAXD = 100;

int R, C;
char grid[MAXR][MAXC];
int distArr[MAXR][MAXC][4];

int dx[4] = {-1, 0, 1, 0};
int dy[4] = {0, 1, 0, -1};

struct State {
    int x, y, dir;
};

vector<int> visitedStamp; // for (posID, dist) pairs
int stampCounter = 1;

vector<int> posStamp; // for positions only
int posStampCounter = 1;

int choose_action(const vector<State>& S) {
    bool can_step = true;
    for (const auto &s : S) {
        int nx = s.x + dx[s.dir];
        int ny = s.y + dy[s.dir];
        if (nx < 1 || nx > R || ny < 1 || ny > C || grid[nx][ny] == '#') {
            can_step = false;
            break;
        }
    }

    static int distPosCount[MAXD + 1];
    int bestScore = INT_MAX;
    int bestAction = 0; // 0=left,1=right,2=step

    for (int action = 0; action < 3; ++action) {
        if (action == 2 && !can_step) continue; // step not allowed

        // reset counts
        for (int d = 0; d <= MAXD; ++d) distPosCount[d] = 0;
        ++stampCounter;

        for (const auto &s : S) {
            int nx = s.x, ny = s.y, nd = s.dir;
            if (action == 0) { // left
                nd = (nd + 3) & 3;
            } else if (action == 1) { // right
                nd = (nd + 1) & 3;
            } else { // step
                nx += dx[nd];
                ny += dy[nd];
            }

            int d2 = distArr[nx][ny][nd];
            if (d2 < 0 || d2 > MAXD) continue; // safety, though shouldn't happen

            int posID = (nx - 1) * C + (ny - 1);
            int key = posID * (MAXD + 1) + d2;

            if (visitedStamp[key] != stampCounter) {
                visitedStamp[key] = stampCounter;
                distPosCount[d2]++;
            }
        }

        int worst = 0;
        for (int d = 0; d <= MAXD; ++d) {
            if (distPosCount[d] > worst) worst = distPosCount[d];
        }

        if (worst < bestScore) {
            bestScore = worst;
            bestAction = action;
        }
    }

    return bestAction;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> R >> C)) return 0;
    string line;
    for (int i = 1; i <= R; ++i) {
        cin >> line;
        for (int j = 1; j <= C; ++j) {
            grid[i][j] = line[j - 1];
        }
    }

    // Precompute distances to wall for each open cell and direction
    memset(distArr, 0, sizeof(distArr));
    for (int i = 1; i <= R; ++i) {
        for (int j = 1; j <= C; ++j) {
            if (grid[i][j] == '#') continue;
            for (int dir = 0; dir < 4; ++dir) {
                int nx = i, ny = j, steps = 0;
                while (true) {
                    nx += dx[dir];
                    ny += dy[dir];
                    if (nx < 1 || nx > R || ny < 1 || ny > C || grid[nx][ny] == '#') break;
                    ++steps;
                }
                distArr[i][j][dir] = steps;
            }
        }
    }

    // Initial set of possible states: all open cells, all directions
    vector<State> S;
    S.reserve(R * C * 4);
    for (int i = 1; i <= R; ++i) {
        for (int j = 1; j <= C; ++j) {
            if (grid[i][j] == '.') {
                for (int dir = 0; dir < 4; ++dir) {
                    S.push_back({i, j, dir});
                }
            }
        }
    }

    int posCount = R * C;
    visitedStamp.assign(posCount * (MAXD + 1), 0);
    posStamp.assign(posCount, 0);

    while (true) {
        int d_in;
        if (!(cin >> d_in)) return 0;
        if (d_in == -1) return 0;

        // Filter states by observed distance
        vector<State> newS;
        newS.reserve(S.size());
        for (const auto &s : S) {
            if (distArr[s.x][s.y][s.dir] == d_in) {
                newS.push_back(s);
            }
        }
        S.swap(newS);

        if (S.empty()) {
            cout << "no" << endl;
            cout.flush();
            return 0;
        }

        // Count distinct positions
        ++posStampCounter;
        int uniquePos = 0;
        int lastPosID = -1;
        for (const auto &s : S) {
            int posID = (s.x - 1) * C + (s.y - 1);
            if (posStamp[posID] != posStampCounter) {
                posStamp[posID] = posStampCounter;
                ++uniquePos;
                lastPosID = posID;
            }
        }

        if (uniquePos == 1) {
            int x = lastPosID / C + 1;
            int y = lastPosID % C + 1;
            cout << "yes " << x << " " << y << endl;
            cout.flush();
            return 0;
        }

        // Choose next action
        int action = choose_action(S); // 0=left,1=right,2=step

        if (action == 0) {
            cout << "left" << endl;
        } else if (action == 1) {
            cout << "right" << endl;
        } else {
            cout << "step" << endl;
        }
        cout.flush();

        // Update states according to chosen action
        vector<State> S2;
        S2.reserve(S.size());
        for (auto s : S) {
            if (action == 0) {
                s.dir = (s.dir + 3) & 3;
            } else if (action == 1) {
                s.dir = (s.dir + 1) & 3;
            } else { // step
                s.x += dx[s.dir];
                s.y += dy[s.dir];
            }
            S2.push_back(s);
        }
        S.swap(S2);
    }

    return 0;
}