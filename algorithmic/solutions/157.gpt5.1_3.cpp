#include <bits/stdc++.h>
using namespace std;

const int MAXN = 10;

int N;
int T;
vector<string> board;
int emptyR, emptyC;
int hexBit[256];

int dr[4] = {-1, 1, 0, 0};
int dc[4] = {0, 0, -1, 1};

void initHexBit() {
    for (int i = 0; i < 256; i++) hexBit[i] = 0;
    for (char c = '0'; c <= '9'; c++) hexBit[(unsigned char)c] = c - '0';
    for (char c = 'a'; c <= 'f'; c++) hexBit[(unsigned char)c] = 10 + (c - 'a');
}

char opposite(char d) {
    if (d == 'U') return 'D';
    if (d == 'D') return 'U';
    if (d == 'L') return 'R';
    return 'L'; // 'R'
}

bool canMove(char dir) {
    if (dir == 'U') return emptyR > 0;
    if (dir == 'D') return emptyR < N - 1;
    if (dir == 'L') return emptyC > 0;
    if (dir == 'R') return emptyC < N - 1;
    return false;
}

void applyMove(char dir) {
    if (dir == 'U') {
        swap(board[emptyR][emptyC], board[emptyR - 1][emptyC]);
        emptyR--;
    } else if (dir == 'D') {
        swap(board[emptyR][emptyC], board[emptyR + 1][emptyC]);
        emptyR++;
    } else if (dir == 'L') {
        swap(board[emptyR][emptyC], board[emptyR][emptyC - 1]);
        emptyC--;
    } else if (dir == 'R') {
        swap(board[emptyR][emptyC], board[emptyR][emptyC + 1]);
        emptyC++;
    }
}

int calc_S() {
    static bool vis[MAXN][MAXN];
    static int parentR[MAXN][MAXN];
    static int parentC[MAXN][MAXN];

    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            vis[i][j] = false;
        }
    }

    int Smax = 0;

    for (int si = 0; si < N; si++) {
        for (int sj = 0; sj < N; sj++) {
            if (board[si][sj] == '0' || vis[si][sj]) continue;

            int qR[100], qC[100];
            int qs = 0, qe = 0;
            bool hasCycle = false;
            int cnt = 0;

            qR[qe] = si;
            qC[qe] = sj;
            qe++;
            vis[si][sj] = true;
            parentR[si][sj] = -1;
            parentC[si][sj] = -1;

            while (qs < qe) {
                int r = qR[qs];
                int c = qC[qs];
                qs++;
                cnt++;
                int bits = hexBit[(unsigned char)board[r][c]];

                for (int dir = 0; dir < 4; dir++) {
                    int nr = r + dr[dir];
                    int nc = c + dc[dir];
                    if (nr < 0 || nr >= N || nc < 0 || nc >= N) continue;
                    if (board[nr][nc] == '0') continue;

                    int bits2 = hexBit[(unsigned char)board[nr][nc]];
                    bool connect = false;
                    if (dir == 0) { // up
                        if ((bits & 2) && (bits2 & 8)) connect = true;
                    } else if (dir == 1) { // down
                        if ((bits & 8) && (bits2 & 2)) connect = true;
                    } else if (dir == 2) { // left
                        if ((bits & 1) && (bits2 & 4)) connect = true;
                    } else { // right
                        if ((bits & 4) && (bits2 & 1)) connect = true;
                    }
                    if (!connect) continue;

                    if (!vis[nr][nc]) {
                        vis[nr][nc] = true;
                        parentR[nr][nc] = r;
                        parentC[nr][nc] = c;
                        qR[qe] = nr;
                        qC[qe] = nc;
                        qe++;
                    } else {
                        if (!(parentR[r][c] == nr && parentC[r][c] == nc)) {
                            hasCycle = true;
                        }
                    }
                }
            }

            if (!hasCycle) {
                if (cnt > Smax) Smax = cnt;
            }
        }
    }

    return Smax;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> T;
    board.assign(N, string());
    emptyR = emptyC = -1;
    for (int i = 0; i < N; i++) {
        cin >> board[i];
        for (int j = 0; j < N; j++) {
            if (board[i][j] == '0') {
                emptyR = i;
                emptyC = j;
            }
        }
    }

    initHexBit();

    int bestS = calc_S();
    int targetS = N * N - 1;

    string ans;
    ans.reserve(T);

    for (int step = 0; step < T; step++) {
        if (bestS == targetS) break;

        char bestDir = '?';
        int bestDirS = -1;

        const char dirs[4] = {'U', 'D', 'L', 'R'};
        for (int k = 0; k < 4; k++) {
            char dir = dirs[k];
            if (!canMove(dir)) continue;
            if (!ans.empty() && opposite(dir) == ans.back()) continue;

            applyMove(dir);
            int s = calc_S();
            applyMove(opposite(dir));

            if (s > bestDirS) {
                bestDirS = s;
                bestDir = dir;
            }
        }

        if (bestDir == '?') break;

        if (bestDirS > bestS || (bestDirS == bestS && bestS < targetS)) {
            applyMove(bestDir);
            ans.push_back(bestDir);
            bestS = bestDirS;
        } else {
            break;
        }
    }

    cout << ans << '\n';
    return 0;
}