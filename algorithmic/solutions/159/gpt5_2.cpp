#include <bits/stdc++.h>
using namespace std;

struct Candidate {
    int xp, yp;
    int xo, yo; // missing corner will be (xo, yo)
    long long score;
    bool operator<(const Candidate& other) const {
        return score < other.score; // for max-heap
    }
};

int N, M;
vector<vector<char>> used;
vector<vector<int>> rowVec, colVec;
unordered_set<uint64_t> edges; // set of unit segments already drawn
vector<array<int,8>> answer;   // operations

inline uint64_t seg_key(int x1, int y1, int x2, int y2) {
    if (x1 > x2 || (x1 == x2 && y1 > y2)) {
        swap(x1, x2);
        swap(y1, y2);
    }
    // each coord fits in 6 bits (0..63)
    return ((uint64_t)x1 << 18) | ((uint64_t)y1 << 12) | ((uint64_t)x2 << 6) | (uint64_t)y2;
}

inline long long weight_point(int x, int y, int c) {
    long long dx = x - c;
    long long dy = y - c;
    return dx*dx + dy*dy + 1;
}

bool checkCandidate(int xp, int yp, int xo, int yo, vector<uint64_t>& newSegs) {
    if (xp == xo || yp == yo) return false; // degenerate
    if (!used[xp][yp]) return false;
    if (!used[xp][yo]) return false;
    if (!used[xo][yp]) return false;
    if (used[xo][yo]) return false; // missing corner must be empty

    int xlo = min(xp, xo), xhi = max(xp, xo);
    int ylo = min(yp, yo), yhi = max(yp, yo);

    // Check no other dots on perimeter (excluding the three existing corners)
    for (int x = xlo + 1; x <= xhi - 1; ++x) {
        if (used[x][ylo]) return false;
        if (used[x][yhi]) return false;
    }
    for (int y = ylo + 1; y <= yhi - 1; ++y) {
        if (used[xlo][y]) return false;
        if (used[xhi][y]) return false;
    }

    // Check edge overlap and collect segments
    newSegs.clear();
    newSegs.reserve(2 * ((xhi - xlo) + (yhi - ylo)));

    // bottom
    for (int x = xlo; x < xhi; ++x) {
        uint64_t k = seg_key(x, ylo, x+1, ylo);
        if (edges.find(k) != edges.end()) return false;
        newSegs.push_back(k);
    }
    // top
    for (int x = xlo; x < xhi; ++x) {
        uint64_t k = seg_key(x, yhi, x+1, yhi);
        if (edges.find(k) != edges.end()) return false;
        newSegs.push_back(k);
    }
    // left
    for (int y = ylo; y < yhi; ++y) {
        uint64_t k = seg_key(xlo, y, xlo, y+1);
        if (edges.find(k) != edges.end()) return false;
        newSegs.push_back(k);
    }
    // right
    for (int y = ylo; y < yhi; ++y) {
        uint64_t k = seg_key(xhi, y, xhi, y+1);
        if (edges.find(k) != edges.end()) return false;
        newSegs.push_back(k);
    }
    return true;
}

void addRectangleAndDot(int xp, int yp, int xo, int yo, const vector<uint64_t>& newSegs) {
    // Place the new dot at (xo, yo)
    used[xo][yo] = 1;
    rowVec[yo].push_back(xo);
    colVec[xo].push_back(yo);

    // Record operation: order D -> E -> F -> G (cyclic around rectangle)
    // D = (xo, yo) [new]
    // E = (xp, yo) [existing]
    // F = (xp, yp) [existing]
    // G = (xo, yp) [existing]
    array<int,8> op = {xo, yo, xp, yo, xp, yp, xo, yp};
    answer.push_back(op);

    // Add segments to drawn set
    for (auto k : newSegs) edges.insert(k);
}

void generate_for_dot(int xp, int yp, priority_queue<Candidate>& pq, int c) {
    // For each y2 in column xp, and for each x2 in row yp, propose missing at (x2, y2)
    for (int yo : colVec[xp]) {
        if (yo == yp) continue;
        for (int xo : rowVec[yp]) {
            if (xo == xp) continue;
            if (used[xo][yo]) continue; // missing must be empty
            // quick early check to avoid degenerate
            if (xo == xp || yo == yp) continue;
            // We will push candidate if currently valid
            vector<uint64_t> segs;
            if (checkCandidate(xp, yp, xo, yo, segs)) {
                Candidate cand;
                cand.xp = xp; cand.yp = yp; cand.xo = xo; cand.yo = yo;
                cand.score = weight_point(xo, yo, c);
                pq.push(cand);
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> M;
    vector<pair<int,int>> initial(M);
    used.assign(N, vector<char>(N, 0));
    rowVec.assign(N, {});
    colVec.assign(N, {});
    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        initial[i] = {x, y};
        used[x][y] = 1;
        rowVec[y].push_back(x);
        colVec[x].push_back(y);
    }

    int c = (N - 1) / 2;

    // Build initial candidates
    priority_queue<Candidate> pq;
    for (auto &p : initial) {
        generate_for_dot(p.first, p.second, pq, c);
    }

    // Main loop
    vector<uint64_t> segs;
    while (!pq.empty()) {
        Candidate cand = pq.top(); pq.pop();
        // re-validate (state could have changed)
        if (!checkCandidate(cand.xp, cand.yp, cand.xo, cand.yo, segs)) continue;
        // commit
        addRectangleAndDot(cand.xp, cand.yp, cand.xo, cand.yo, segs);
        // generate new candidates for the new dot
        generate_for_dot(cand.xo, cand.yo, pq, c);
    }

    // Output
    cout << (int)answer.size() << '\n';
    for (auto &op : answer) {
        cout << op[0] << ' ' << op[1] << ' ' << op[2] << ' ' << op[3] << ' '
             << op[4] << ' ' << op[5] << ' ' << op[6] << ' ' << op[7] << '\n';
    }
    return 0;
}