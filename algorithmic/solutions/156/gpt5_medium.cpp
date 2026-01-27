#include <bits/stdc++.h>
using namespace std;

static const int N = 30;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<string> rows;
    rows.reserve(N);
    vector<vector<int>> orig(N, vector<int>(N));

    // Read input: handle both 30-character lines or 900 tokens
    vector<string> tokens;
    tokens.reserve(N * N);
    {
        string s;
        while (cin >> s) tokens.push_back(s);
    }
    if (tokens.size() == N) {
        // Each token is a 30-char string
        for (int i = 0; i < N; ++i) {
            string &row = tokens[i];
            for (int j = 0; j < N; ++j) {
                orig[i][j] = row[j] - '0';
            }
        }
    } else {
        // Assume 900 single char tokens
        int idx = 0;
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                orig[i][j] = tokens[idx][0] - '0';
                idx++;
            }
        }
    }

    // Direction: 0:left,1:up,2:right,3:down
    int di[4] = {0, -1, 0, 1};
    int dj[4] = {-1, 0, 1, 0};

    // to[t][d]: exit direction when entering tile of type t from direction d
    int to[8][4] = {
        {1, 0, -1, -1},
        {3, -1, -1, 0},
        {-1, -1, 3, 2},
        {-1, 2, 1, -1},
        {1, 0, 3, 2},
        {3, 2, 1, 0},
        {2, -1, 0, -1},
        {-1, 3, -1, 1},
    };

    // Rotation mapping: CCW rotation 90 deg
    int rotCCW[8] = {1,2,3,0,5,4,7,6};

    auto rotateType = [&](int t, int r)->int{
        r &= 3;
        while (r--) t = rotCCW[t];
        return t;
    };

    // Precompute "entry direction for side s" ent[t][s], s=0..3 (left,up,right,down)
    // ent[t][s] = d such that to[t][d] == s, otherwise -1
    int ent[8][4];
    for (int t = 0; t < 8; ++t) {
        for (int s = 0; s < 4; ++s) ent[t][s] = -1;
        for (int d = 0; d < 4; ++d) {
            int e = to[t][d];
            if (e >= 0) ent[t][e] = d;
        }
    }

    // Initialize rotations randomly
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist4(0,3);
    vector<vector<int>> rot(N, vector<int>(N, 0));
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            rot[i][j] = dist4(rng);

    // Compute current types after rotation
    vector<vector<int>> tp(N, vector<int>(N, 0));
    auto updateTypes = [&](){
        for (int i = 0; i < N; ++i)
            for (int j = 0; j < N; ++j)
                tp[i][j] = rotateType(orig[i][j], rot[i][j]);
    };
    updateTypes();

    // Local greedy to maximize matched edges
    auto localScoreFor = [&](int i, int j, int r)->int{
        int tHere = rotateType(orig[i][j], r);
        int score = 0;
        for (int s = 0; s < 4; ++s) {
            if (ent[tHere][s] == -1) continue; // no connection on side s
            int ni = i + di[s], nj = j + dj[s];
            if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
            int tN = tp[ni][nj];
            if (ent[tN][(s+2)%4] != -1) score++;
        }
        return score;
    };

    // Perform a few passes of coordinate ascent
    vector<int> order(N*N);
    iota(order.begin(), order.end(), 0);
    for (int pass = 0; pass < 2; ++pass) {
        shuffle(order.begin(), order.end(), rng);
        for (int idx = 0; idx < N*N; ++idx) {
            int i = order[idx] / N;
            int j = order[idx] % N;
            int bestR = rot[i][j];
            int bestVal = localScoreFor(i, j, bestR);
            for (int rr = 0; rr < 4; ++rr) {
                if (rr == rot[i][j]) continue;
                int val = localScoreFor(i, j, rr);
                if (val > bestVal || (val == bestVal && dist4(rng) == 0)) {
                    bestVal = val;
                    bestR = rr;
                }
            }
            if (bestR != rot[i][j]) {
                rot[i][j] = bestR;
                tp[i][j] = rotateType(orig[i][j], rot[i][j]);
            }
        }
    }

    // Function to evaluate score L1*L2 by computing cycles on state graph (i,j,d)
    auto evaluateScore = [&]()->long long{
        const int S = N * N * 4;
        static vector<int> nxt;
        nxt.assign(S, -1);
        auto idx = [&](int i, int j, int d){ return ((i * N + j) << 2) | d; };
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                int t = tp[i][j];
                for (int d = 0; d < 4; ++d) {
                    int d2 = to[t][d];
                    if (d2 == -1) continue;
                    int ni = i + di[d2], nj = j + dj[d2];
                    if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
                    int nd = (d2 + 2) & 3;
                    nxt[idx(i,j,d)] = idx(ni,nj,nd);
                }
            }
        }
        static vector<char> col;
        col.assign(S, 0);
        long long L1 = 0, L2 = 0;
        for (int s = 0; s < S; ++s) {
            if (col[s] || nxt[s] == -1) { col[s] = 2; continue; }
            int u = s;
            vector<int> path;
            while (true) {
                col[u] = 1;
                path.push_back(u);
                int v = nxt[u];
                if (v == -1) {
                    for (int x : path) col[x] = 2;
                    break;
                }
                if (col[v] == 0) {
                    u = v;
                    continue;
                } else if (col[v] == 1) {
                    // found cycle
                    int cycLen = 1;
                    for (int k = (int)path.size()-1; k >= 0; --k) {
                        if (path[k] == v) break;
                        cycLen++;
                    }
                    // update top two
                    if (cycLen >= L1) {
                        L2 = L1; L1 = cycLen;
                    } else if (cycLen > L2) {
                        L2 = cycLen;
                    }
                    for (int x : path) col[x] = 2;
                    break;
                } else {
                    // col[v] == 2
                    for (int x : path) col[x] = 2;
                    break;
                }
            }
        }
        return (L2 > 0 ? L1 * L2 : 0LL);
    };

    long long curScore = evaluateScore();
    vector<vector<int>> bestRot = rot;
    long long bestScore = curScore;

    // Hill climbing with time limit
    const int TIME_LIMIT_MS = 1800;
    auto startTime = chrono::steady_clock::now();

    uniform_int_distribution<int> distN(0, N-1);
    int iter = 0;
    while (true) {
        iter++;
        // Check time
        if ((iter & 255) == 0) {
            auto now = chrono::steady_clock::now();
            int elapsed = (int)chrono::duration_cast<chrono::milliseconds>(now - startTime).count();
            if (elapsed >= TIME_LIMIT_MS) break;
        }
        int i = distN(rng), j = distN(rng);
        int oldr = rot[i][j];
        int newr = dist4(rng);
        if (newr == oldr) continue;
        rot[i][j] = newr;
        int oldt = tp[i][j];
        tp[i][j] = rotateType(orig[i][j], newr);

        long long newScore = evaluateScore();
        if (newScore >= curScore || (newScore > 0 && dist4(rng) == 0)) {
            curScore = newScore;
            if (curScore > bestScore) {
                bestScore = curScore;
                bestRot = rot;
            }
        } else {
            // revert
            rot[i][j] = oldr;
            tp[i][j] = oldt;
        }
    }

    // Output best rotations as a single 900-character string
    string out;
    out.reserve(N*N);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) out.push_back(char('0' + bestRot[i][j]));
    }
    cout << out << '\n';
    return 0;
}