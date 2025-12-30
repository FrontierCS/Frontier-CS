#include <bits/stdc++.h>
using namespace std;

struct Candidate {
    string row;
    vector<int> covered; // indices in original list covered by this row
};

static inline string repeat_to_length(const string& s, int N) {
    string res;
    res.reserve(N);
    while ((int)res.size() + (int)s.size() <= N) res += s;
    if ((int)res.size() < N) res += s.substr(0, N - (int)res.size());
    return res;
}

static inline bool contains_substring(const string& a, const string& b) {
    // does a contain b
    return a.find(b) != string::npos;
}

static inline int overlap_suffix_prefix(const string& a, const string& b) {
    int la = (int)a.size(), lb = (int)b.size();
    int mx = min(la, lb);
    for (int k = mx; k >= 1; --k) {
        bool ok = true;
        for (int i = 0; i < k; ++i) {
            if (a[la - k + i] != b[i]) { ok = false; break; }
        }
        if (ok) return k;
    }
    return 0;
}

static inline string merge_ab(const string& a, const string& b) {
    if (contains_substring(a, b)) return a;
    int ol = overlap_suffix_prefix(a, b);
    return a + b.substr(ol);
}

static vector<int> computeCoverage(const string& row, const unordered_map<string, vector<int>>& idxs, vector<int>& seen, int& stamp, int M, int maxK) {
    vector<int> res;
    ++stamp;
    int N = (int)row.size();
    int extK = min(maxK - 1, N - 1);
    string ext = row + row.substr(0, extK);
    for (int len = 2; len <= maxK && len <= N; ++len) {
        for (int j = 0; j < N; ++j) {
            string w = ext.substr(j, len);
            auto it = idxs.find(w);
            if (it != idxs.end()) {
                const auto& vec = it->second;
                for (int id : vec) {
                    if (seen[id] != stamp) {
                        seen[id] = stamp;
                        res.push_back(id);
                    }
                }
            }
        }
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    vector<string> s(M);
    for (int i = 0; i < M; ++i) cin >> s[i];

    // Build map from string to list of indices
    unordered_map<string, vector<int>> idxs;
    idxs.reserve(M * 2);
    for (int i = 0; i < M; ++i) {
        idxs[s[i]].push_back(i);
    }

    // Unique strings list
    vector<pair<string,int>> uniq; // (string, freq)
    uniq.reserve(idxs.size());
    for (auto &kv : idxs) uniq.push_back({kv.first, (int)kv.second.size()});

    // Shuffle unique strings for randomness
    mt19937 rng(1234567);
    shuffle(uniq.begin(), uniq.end(), rng);

    // Prepare candidates
    vector<Candidate> cands;
    cands.reserve(30000);
    unordered_set<string> usedRows;
    usedRows.reserve(40000);

    const int MAXK = 12;

    vector<int> seen(M, 0);
    int stamp = 0;

    // Add single-string repeated candidates (tile to length N)
    for (auto &p : uniq) {
        string base = p.first;
        string row = repeat_to_length(base, N);
        if (usedRows.insert(row).second) {
            auto covered = computeCoverage(row, idxs, seen, stamp, M, MAXK);
            if (!covered.empty()) cands.push_back({row, move(covered)});
        }
    }

    // Prepare order for seeds
    vector<int> order(uniq.size());
    iota(order.begin(), order.end(), 0);
    shuffle(order.begin(), order.end(), rng);

    int U = (int)uniq.size();
    int Kseeds = min(200, U);
    int Rsample = min(80, max(0, U - 1));

    // Pair merges
    for (int si = 0; si < Kseeds; ++si) {
        int i = order[si];
        const string &a = uniq[i].first;
        // sample Rsample others
        for (int t = 0; t < Rsample; ++t) {
            int j = uniform_int_distribution<int>(0, U - 1)(rng);
            if (j == i) continue;
            const string &b = uniq[j].first;

            // Two orientations
            string ab = merge_ab(a, b);
            if ((int)ab.size() <= N) {
                string row = repeat_to_length(ab, N);
                if (usedRows.insert(row).second) {
                    auto covered = computeCoverage(row, idxs, seen, stamp, M, MAXK);
                    if (!covered.empty()) cands.push_back({row, move(covered)});
                }
            }
            string ba = merge_ab(b, a);
            if ((int)ba.size() <= N) {
                string row = repeat_to_length(ba, N);
                if (usedRows.insert(row).second) {
                    auto covered = computeCoverage(row, idxs, seen, stamp, M, MAXK);
                    if (!covered.empty()) cands.push_back({row, move(covered)});
                }
            }
        }
    }

    // Add some random Markov-chain based candidates for variety
    // Build frequency and transition counts
    array<long long, 8> freq{};
    array<array<long long, 8>, 8> trans{};
    for (auto &str : s) {
        if (str.empty()) continue;
        for (char ch : str) freq[ch - 'A']++;
        for (int i = 0; i + 1 < (int)str.size(); ++i) {
            int u = str[i] - 'A';
            int v = str[i+1] - 'A';
            if (0 <= u && u < 8 && 0 <= v && v < 8) trans[u][v]++;
        }
    }
    long long sumFreq = 0;
    for (int c = 0; c < 8; ++c) sumFreq += freq[c];
    auto pickStart = [&](mt19937 &rng)->int{
        if (sumFreq == 0) return uniform_int_distribution<int>(0,7)(rng);
        uniform_int_distribution<long long> dist(1, sumFreq);
        long long x = dist(rng);
        long long acc = 0;
        for (int c = 0; c < 8; ++c) {
            acc += freq[c];
            if (x <= acc) return c;
        }
        return 0;
    };
    auto pickNext = [&](int prev, mt19937 &rng)->int{
        long long tot = 0;
        for (int c = 0; c < 8; ++c) tot += trans[prev][c];
        if (tot == 0) return uniform_int_distribution<int>(0,7)(rng);
        uniform_int_distribution<long long> dist(1, tot);
        long long x = dist(rng);
        long long acc = 0;
        for (int c = 0; c < 8; ++c) {
            acc += trans[prev][c];
            if (x <= acc) return c;
        }
        return 0;
    };

    int randCands = 200;
    for (int t = 0; t < randCands; ++t) {
        string row;
        row.resize(N);
        int cur = pickStart(rng);
        row[0] = char('A' + cur);
        for (int i = 1; i < N; ++i) {
            cur = pickNext(cur, rng);
            row[i] = char('A' + cur);
        }
        if (usedRows.insert(row).second) {
            auto covered = computeCoverage(row, idxs, seen, stamp, M, MAXK);
            if (!covered.empty()) cands.push_back({row, move(covered)});
        }
    }

    // Greedy selection of up to N rows
    vector<char> covered(M, 0);
    vector<string> rows;
    rows.reserve(N);

    for (int it = 0; it < N; ++it) {
        int bestId = -1, bestGain = -1, bestTotal = -1;
        for (int i = 0; i < (int)cands.size(); ++i) {
            const auto &cand = cands[i];
            int gain = 0;
            for (int id : cand.covered) {
                if (!covered[id]) ++gain;
            }
            if (gain > bestGain || (gain == bestGain && (int)cand.covered.size() > bestTotal)) {
                bestGain = gain;
                bestTotal = (int)cand.covered.size();
                bestId = i;
            }
        }
        if (bestId == -1 || bestGain <= 0) {
            // No improvement; fill remaining with simple pattern
            break;
        }
        rows.push_back(cands[bestId].row);
        for (int id : cands[bestId].covered) covered[id] = 1;
    }

    // If not enough rows, fill with some fallback patterns
    // Use repeating patterns from alphabet
    vector<string> fallback;
    // create 8 simple periodic patterns
    for (int p = 1; p <= 8; ++p) {
        string base;
        for (int i = 0; i < p; ++i) base += char('A' + i);
        fallback.push_back(repeat_to_length(base, N));
    }
    int fi = 0;
    while ((int)rows.size() < N) {
        rows.push_back(fallback[fi % (int)fallback.size()]);
        ++fi;
    }

    // Output matrix: rows
    for (int i = 0; i < N; ++i) {
        cout << rows[i] << '\n';
    }

    return 0;
}