#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 20;

struct Node {
    int idx;
    int len;
    uint32_t key;
};

int N, M;
vector<string> S;

bool placeString(const string &s, vector<string> &board) {
    int k = (int)s.size();
    int bestOverlap = -1;
    int bestNewCells = INT_MAX;
    int bestDir = -1, bestI = -1, bestJ = -1;

    // Horizontal
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int overlap = 0, newCells = 0;
            bool ok = true;
            int c = j;
            for (int p = 0; p < k; ++p) {
                char cur = board[i][c];
                char ch = s[p];
                if (cur == '.') newCells++;
                else if (cur == ch) overlap++;
                else { ok = false; break; }
                ++c; if (c == N) c = 0;
            }
            if (!ok) continue;
            if (overlap > bestOverlap || (overlap == bestOverlap && newCells < bestNewCells)) {
                bestOverlap = overlap;
                bestNewCells = newCells;
                bestDir = 0;
                bestI = i;
                bestJ = j;
            }
        }
    }

    // Vertical
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int overlap = 0, newCells = 0;
            bool ok = true;
            int r = i;
            for (int p = 0; p < k; ++p) {
                char cur = board[r][j];
                char ch = s[p];
                if (cur == '.') newCells++;
                else if (cur == ch) overlap++;
                else { ok = false; break; }
                ++r; if (r == N) r = 0;
            }
            if (!ok) continue;
            if (overlap > bestOverlap || (overlap == bestOverlap && newCells < bestNewCells)) {
                bestOverlap = overlap;
                bestNewCells = newCells;
                bestDir = 1;
                bestI = i;
                bestJ = j;
            }
        }
    }

    if (bestOverlap < 0) return false;

    // Apply best placement
    int i = bestI, j = bestJ;
    if (bestDir == 0) {
        int c = j;
        for (int p = 0; p < k; ++p) {
            char ch = s[p];
            if (board[i][c] == '.') board[i][c] = ch;
            ++c; if (c == N) c = 0;
        }
    } else {
        int r = i;
        for (int p = 0; p < k; ++p) {
            char ch = s[p];
            if (board[r][j] == '.') board[r][j] = ch;
            ++r; if (r == N) r = 0;
        }
    }
    return true;
}

int countMatches(const vector<string> &board) {
    int cnt = 0;
    for (int idx = 0; idx < M; ++idx) {
        const string &s = S[idx];
        int k = (int)s.size();
        bool matched = false;

        // Horizontal
        for (int i = 0; i < N && !matched; ++i) {
            for (int j = 0; j < N && !matched; ++j) {
                bool ok = true;
                int c = j;
                for (int p = 0; p < k; ++p) {
                    if (board[i][c] != s[p]) { ok = false; break; }
                    ++c; if (c == N) c = 0;
                }
                if (ok) { matched = true; break; }
            }
        }

        // Vertical
        for (int i = 0; i < N && !matched; ++i) {
            for (int j = 0; j < N && !matched; ++j) {
                bool ok = true;
                int r = i;
                for (int p = 0; p < k; ++p) {
                    if (board[r][j] != s[p]) { ok = false; break; }
                    ++r; if (r == N) r = 0;
                }
                if (ok) { matched = true; break; }
            }
        }

        if (matched) ++cnt;
    }
    return cnt;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> M;
    S.resize(M);
    for (int i = 0; i < M; ++i) cin >> S[i];

    // Global character frequency
    long long freq[8] = {};
    for (int i = 0; i < M; ++i) {
        for (char ch : S[i]) {
            if (ch >= 'A' && ch <= 'H') freq[ch - 'A']++;
        }
    }
    int bestCharIdx = 0;
    for (int c = 1; c < 8; ++c) {
        if (freq[c] > freq[bestCharIdx]) bestCharIdx = c;
    }
    char fillChar = char('A' + bestCharIdx);

    mt19937_64 rng(123456789);

    const int RESTARTS = 7;
    vector<string> bestBoard(N, string(N, fillChar));
    int bestScore = -1;

    for (int rep = 0; rep < RESTARTS; ++rep) {
        vector<string> board(N, string(N, '.'));

        vector<Node> nodes(M);
        for (int i = 0; i < M; ++i) {
            nodes[i].idx = i;
            nodes[i].len = (int)S[i].size();
            nodes[i].key = (uint32_t)rng();
        }
        sort(nodes.begin(), nodes.end(), [](const Node &a, const Node &b) {
            if (a.len != b.len) return a.len > b.len; // longer first
            return a.key < b.key; // random tie-break
        });

        for (const auto &nd : nodes) {
            const string &str = S[nd.idx];
            placeString(str, board);
        }

        // Fill remaining '.' with fillChar
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (board[i][j] == '.') board[i][j] = fillChar;
            }
        }

        int score = countMatches(board);
        if (score > bestScore) {
            bestScore = score;
            bestBoard = board;
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << bestBoard[i] << '\n';
    }

    return 0;
}