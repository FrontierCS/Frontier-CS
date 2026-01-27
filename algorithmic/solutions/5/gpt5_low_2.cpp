#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char getcharFast() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template <typename T>
    bool readInt(T &out) {
        char c; T sign = 1; T val = 0;
        c = getcharFast();
        if (!c) return false;
        while (c!='-' && (c<'0' || c>'9')) {
            c = getcharFast();
            if (!c) return false;
        }
        if (c=='-') { sign = -1; c = getcharFast(); }
        for (; c>='0' && c<='9'; c=getcharFast())
            val = val*10 + (c - '0');
        out = val * sign;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);
    // read scoring params, but unused for algorithm
    for (int i = 0; i < 10; ++i) {
        int tmp; fs.readInt(tmp);
    }
    vector<vector<int>> out(n+1), in(n+1);
    out.reserve(n+1); in.reserve(n+1);
    out.shrink_to_fit(); in.shrink_to_fit();
    vector<int> degOut(n+1,0), degIn(n+1,0);
    for (int i = 0; i < m; ++i) {
        int u, v; fs.readInt(u); fs.readInt(v);
        out[u].push_back(v);
        in[v].push_back(u);
        degOut[u]++; degIn[v]++;
    }

    // Shuffle adjacency for randomness
    std::mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    for (int i = 1; i <= n; ++i) {
        auto &vo = out[i];
        if (!vo.empty()) shuffle(vo.begin(), vo.end(), rng);
        auto &vi = in[i];
        if (!vi.empty()) shuffle(vi.begin(), vi.end(), rng);
    }

    // Candidate seeds: high degree nodes and random picks
    vector<int> nodes(n);
    iota(nodes.begin(), nodes.end(), 1);
    // compute combined degree
    vector<pair<long long,int>> degScore;
    degScore.reserve(n);
    for (int i = 1; i <= n; ++i) {
        degScore.emplace_back((long long)degOut[i] + (long long)degIn[i], i);
    }
    sort(degScore.begin(), degScore.end(), greater<pair<long long,int>>());

    vector<int> seeds;
    int topK = min(n, 10);
    for (int i = 0; i < topK; ++i) seeds.push_back(degScore[i].second);
    // also include max outdeg and max indeg
    int maxOut = max_element(degOut.begin()+1, degOut.end()) - degOut.begin();
    int maxIn  = max_element(degIn.begin()+1, degIn.end()) - degIn.begin();
    seeds.push_back(maxOut);
    seeds.push_back(maxIn);
    // add some random seeds
    uniform_int_distribution<int> distNode(1, n);
    for (int i = 0; i < 8 && (int)seeds.size() < 25; ++i) seeds.push_back(distNode(rng));
    // deduplicate seeds
    sort(seeds.begin(), seeds.end());
    seeds.erase(unique(seeds.begin(), seeds.end()), seeds.end());

    vector<int> visStamp(n+1, 0);
    int stamp = 1;

    vector<int> bestPath;
    bestPath.reserve(n);

    auto attempt = [&](int s)->vector<int> {
        vector<int> pathVec;
        pathVec.reserve(n);
        deque<int> dq;
        int head, tail;
        int curStamp = stamp++;
        if (curStamp == 0) { // overflow safety, unlikely
            fill(visStamp.begin(), visStamp.end(), 0);
            curStamp = ++stamp;
        }
        dq.clear();
        dq.push_back(s);
        visStamp[s] = curStamp;
        head = tail = s;

        while (true) {
            bool extended = false;
            // try extend tail via outgoing edges
            {
                int t = tail;
                auto &vo = out[t];
                for (int v : vo) {
                    if (visStamp[v] != curStamp) {
                        dq.push_back(v);
                        visStamp[v] = curStamp;
                        tail = v;
                        extended = true;
                        break;
                    }
                }
            }
            if (extended) continue;
            // try extend head via incoming edges
            {
                int h = head;
                auto &vi = in[h];
                for (int u : vi) {
                    if (visStamp[u] != curStamp) {
                        dq.push_front(u);
                        visStamp[u] = curStamp;
                        head = u;
                        extended = true;
                        break;
                    }
                }
            }
            if (!extended) break;
        }
        pathVec.assign(dq.begin(), dq.end());
        return pathVec;
    };

    auto startTime = chrono::steady_clock::now();
    const double timeLimit = 3.5; // seconds, keep under 4s
    for (int s : seeds) {
        auto cur = attempt(s);
        if (cur.size() > bestPath.size()) bestPath.swap(cur);
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - startTime).count();
        if (elapsed > timeLimit) break;
    }
    // If nothing found (shouldn't happen), pick any node
    if (bestPath.empty()) bestPath.push_back(1);

    // Output
    cout << bestPath.size() << "\n";
    for (size_t i = 0; i < bestPath.size(); ++i) {
        if (i) cout << ' ';
        cout << bestPath[i];
    }
    cout << "\n";
    return 0;
}