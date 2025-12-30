#include <bits/stdc++.h>
using namespace std;

static const int N = 30;
static const int di[4] = {0, -1, 0, 1};  // left, up, right, down
static const int dj[4] = {-1, 0, 1, 0};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // Read input (robust: supports both 30-char strings and 30 single digits per line)
    int base[N][N];
    for (int i = 0; i < N; i++) {
        string s;
        if (!(cin >> s)) return 0;
        if ((int)s.size() == N) {
            for (int j = 0; j < N; j++) base[i][j] = s[j] - '0';
        } else if ((int)s.size() == 1) {
            base[i][0] = s[0] - '0';
            for (int j = 1; j < N; j++) {
                string t;
                cin >> t;
                base[i][j] = t[0] - '0';
            }
        } else {
            // Fallback: read 30 tokens
            vector<int> row;
            row.reserve(N);
            // parse s as first token(s) if it contains digits
            for (char c : s) {
                if ('0' <= c && c <= '7') row.push_back(c - '0');
            }
            while ((int)row.size() < N) {
                string t; cin >> t;
                for (char c : t) {
                    if ('0' <= c && c <= '7') {
                        row.push_back(c - '0');
                        if ((int)row.size() == N) break;
                    }
                }
            }
            for (int j = 0; j < N; j++) base[i][j] = row[j];
        }
    }

    // to[t][d] mapping as given
    static const int toMap[8][4] = {
        {1, 0, -1, -1},
        {3, -1, -1, 0},
        {-1, -1, 3, 2},
        {-1, 2, 1, -1},
        {1, 0, 3, 2},
        {3, 2, 1, 0},
        {2, -1, 0, -1},
        {-1, 3, -1, 1},
    };
    // Open sides
    bool open[8][4];
    for (int t = 0; t < 8; t++) {
        for (int d = 0; d < 4; d++) open[t][d] = (toMap[t][d] != -1);
    }
    // Rotation mapping (90 deg CCW)
    int rot90[8] = {1,2,3,0,5,4,7,6};
    auto rotType = [&](int t, int r) {
        r &= 3;
        while (r--) t = rot90[t];
        return t;
    };

    // Initial rotations
    vector<vector<int>> rot(N, vector<int>(N, 0));
    // Randomize rotations for types 4 and 5 to diversify
    unsigned seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    std::mt19937_64 rng(seed);
    std::uniform_int_distribution<int> rotDist(0,3);

    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) {
        if (base[i][j] == 4 || base[i][j] == 5) {
            rot[i][j] = rotDist(rng);
        } else {
            rot[i][j] = 0;
        }
    }

    // Helper: get oriented type
    auto getType = [&](int i, int j) {
        return rotType(base[i][j], rot[i][j]);
    };

    // Greedy coordinate descent to maximize edge matches and minimize open boundaries
    auto inb = [&](int i, int j){ return (0 <= i && i < N && 0 <= j && j < N); };
    auto localScore = [&](int i, int j, int rtest) {
        int t = rotType(base[i][j], rtest);
        int score = 0;
        for (int s = 0; s < 4; s++) {
            int ni = i + di[s], nj = j + dj[s];
            if (inb(ni,nj)) {
                int tnb = getType(ni,nj);
                if (open[t][s] && open[tnb][(s+2)&3]) score += 1;
            } else {
                if (open[t][s]) score -= 1; // penalty for open to outside
            }
        }
        return score;
    };

    // Only adjust tiles where rotation affects open sides (i.e., not types 4/5)
    for (int pass = 0; pass < 6; pass++) {
        int changes = 0;
        for (int i = 0; i < N; i++) {
            for (int j = 0; j < N; j++) {
                int t0 = base[i][j];
                if (t0 == 4 || t0 == 5) continue; // both rotations keep all sides open; leave for later
                int bestR = rot[i][j];
                int bestS = INT_MIN;
                for (int rtest = 0; rtest < 4; rtest++) {
                    int sc = localScore(i,j,rtest);
                    if (sc > bestS) { bestS = sc; bestR = rtest; }
                }
                if (bestR != rot[i][j]) { rot[i][j] = bestR; changes++; }
            }
        }
        if (changes == 0) break;
    }

    // Function to compute product of top two loop lengths for current rotation
    auto computeScoreProduct = [&]()->long long {
        // Build oriented types
        static int T[N][N];
        for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) T[i][j] = rotType(base[i][j], rot[i][j]);
        int totalStates = N*N*4;
        vector<char> visited(totalStates, 0);
        vector<int> idxMap(totalStates, -1);
        vector<int> loops;
        loops.reserve(2000);

        auto idEnc = [&](int i, int j, int d){ return ((i * N + j) << 2) | d; };
        auto idDec = [&](int id, int &i, int &j, int &d){
            d = id & 3;
            int k = id >> 2;
            i = k / N;
            j = k % N;
        };

        for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) {
            int t = T[i][j];
            for (int d = 0; d < 4; d++) {
                if (!open[t][d]) continue;
                int start = idEnc(i,j,d);
                if (visited[start]) continue;

                vector<int> path;
                path.reserve(256);

                int ci = i, cj = j, cd = d;
                int cur = start;
                bool hasCycle = false;
                int cycleLen = 0;

                while (true) {
                    if (visited[cur]) {
                        // Already processed in earlier iteration; no cycle from this start
                        hasCycle = false;
                        break;
                    }
                    visited[cur] = 1;
                    idxMap[cur] = (int)path.size();
                    path.push_back(cur);

                    int ii, jj, dd;
                    idDec(cur, ii, jj, dd);
                    int tt = T[ii][jj];
                    int d2 = toMap[tt][dd];
                    if (d2 == -1) { hasCycle = false; break; }
                    int ni = ii + di[d2], nj = jj + dj[d2];
                    if (!inb(ni,nj)) { hasCycle = false; break; }
                    int nd = (d2 + 2) & 3;
                    int nt = T[ni][nj];
                    if (!open[nt][nd]) { hasCycle = false; break; }

                    int next = idEnc(ni,nj,nd);
                    if (idxMap[next] != -1) {
                        // Found cycle
                        int idx = idxMap[next];
                        cycleLen = (int)path.size() - idx;
                        hasCycle = true;
                        break;
                    }
                    cur = next;
                }
                if (hasCycle) loops.push_back(cycleLen);

                // cleanup idxMap for path
                for (int pid : path) idxMap[pid] = -1;
            }
        }
        if (loops.empty()) return 0LL;
        sort(loops.begin(), loops.end(), greater<int>());
        long long L1 = loops[0];
        long long L2 = (loops.size() >= 2 ? loops[1] : loops[0]);
        return L1 * L2;
    };

    // Limited hill-climbing on types 4/5 to try improving loop product
    auto get_time = []() -> double {
        using namespace std::chrono;
        static auto st = high_resolution_clock::now();
        auto now = high_resolution_clock::now();
        return duration<double>(now - st).count();
    };

    long long bestScore = computeScoreProduct();
    long long curScore = bestScore;
    vector<vector<int>> bestRot = rot;

    double timeLimit = 1.9; // seconds
    // Try random flips for types 4/5 only
    vector<pair<int,int>> candidates;
    candidates.reserve(N*N);
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) {
        if (base[i][j] == 4 || base[i][j] == 5) candidates.emplace_back(i,j);
    }

    if (!candidates.empty()) {
        uniform_int_distribution<int> candDist(0, (int)candidates.size() - 1);
        uniform_int_distribution<int> rset(0,3);
        // A simple hill-climb loop
        int iter = 0;
        while (get_time() < timeLimit) {
            iter++;
            auto [i, j] = candidates[candDist(rng)];
            int oldr = rot[i][j];
            int newr = rset(rng);
            if (newr == oldr) continue;
            rot[i][j] = newr;
            long long nscore = computeScoreProduct();
            if (nscore >= curScore) {
                curScore = nscore;
                if (curScore > bestScore) {
                    bestScore = curScore;
                    bestRot = rot;
                }
            } else {
                // revert
                rot[i][j] = oldr;
            }
        }
        rot = bestRot;
    }

    // Output rotations as a single 900-length string
    string out;
    out.reserve(N*N);
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) {
        int r = rot[i][j] & 3;
        out.push_back(char('0' + r));
    }
    cout << out << "\n";
    return 0;
}