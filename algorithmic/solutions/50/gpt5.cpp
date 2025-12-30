#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return EOF;
        }
        return buf[idx++];
    }
    template <typename T>
    bool nextInt(T &out) {
        char c;
        T sign = 1;
        T val = 0;
        c = getChar();
        if (c == EOF) return false;
        // Skip non-numeric
        while (c <= ' ') {
            c = getChar();
            if (c == EOF) return false;
        }
        if (c == '-') { sign = -1; c = getChar(); }
        for (; c > ' '; c = getChar()) {
            if (c < '0' || c > '9') break;
            val = val * 10 + (c - '0');
        }
        out = val * sign;
        return true;
    }
};

struct Node {
    double key;
    int cnt;
    int id;
};
struct Cmp {
    bool operator()(const Node &a, const Node &b) const {
        if (a.key == b.key) {
            if (a.cnt == b.cnt) return a.id > b.id;
            return a.cnt < b.cnt; // prefer larger coverage on tie
        }
        return a.key > b.key; // min-heap by key
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // Use FastScanner for speed
    FastScanner fs;
    int n, m;
    if (!fs.nextInt(n)) return 0;
    fs.nextInt(m);

    vector<long long> cost(m + 1, 0);
    for (int i = 1; i <= m; ++i) fs.nextInt(cost[i]);

    vector<vector<int>> elemSets(n + 1);
    vector<vector<int>> setElems(m + 1);

    long long sumK = 0;
    for (int i = 1; i <= n; ++i) {
        int k; fs.nextInt(k);
        elemSets[i].reserve(k);
        sumK += k;
        for (int j = 0; j < k; ++j) {
            int a; fs.nextInt(a);
            elemSets[i].push_back(a);
            setElems[a].push_back(i);
        }
    }

    vector<int> coverableCount(m + 1, 0);
    vector<char> chosen(m + 1, 0);
    vector<char> uncovered(n + 1, 1);

    int remainUncovered = n;

    // Initialize coverableCount
    for (int s = 1; s <= m; ++s) {
        coverableCount[s] = (int)setElems[s].size();
    }

    auto chooseSet = [&](int s, auto &heap) {
        if (chosen[s]) return;
        chosen[s] = 1;
        // For each newly covered element by s, update others' coverableCount
        for (int e : setElems[s]) {
            if (uncovered[e]) {
                uncovered[e] = 0;
                --remainUncovered;
                for (int t : elemSets[e]) {
                    if (coverableCount[t] > 0) {
                        --coverableCount[t];
                        if (!chosen[t] && coverableCount[t] > 0) {
                            double key = (double)cost[t] / (double)coverableCount[t];
                            heap.push(Node{key, coverableCount[t], t});
                        }
                    }
                }
            }
        }
    };

    // Priority queue declared here to pass reference to lambda
    priority_queue<Node, vector<Node>, Cmp> heap;

    // Preselect sets that are the only ones covering some element
    for (int e = 1; e <= n; ++e) {
        if ((int)elemSets[e].size() == 1) {
            int s = elemSets[e][0];
            if (!chosen[s]) {
                // chooseSet uses heap; ensure heap exists (it's empty now)
                chooseSet(s, heap);
            }
        }
    }

    // Initialize heap with all not-yet-chosen sets that can cover some uncovered elements
    for (int s = 1; s <= m; ++s) {
        if (!chosen[s] && coverableCount[s] > 0) {
            double key = (double)cost[s] / (double)coverableCount[s];
            heap.push(Node{key, coverableCount[s], s});
        }
    }

    // Greedy selection
    while (remainUncovered > 0) {
        if (heap.empty()) {
            // No set can cover remaining elements; fallback: pick any set containing an uncovered element
            // This should not happen if input is valid, but handle defensively
            int picked = -1;
            for (int s = 1; s <= m; ++s) {
                if (!chosen[s]) {
                    bool helps = false;
                    for (int e : setElems[s]) {
                        if (uncovered[e]) { helps = true; break; }
                    }
                    if (helps) { picked = s; break; }
                }
            }
            if (picked == -1) break; // cannot cover further
            chooseSet(picked, heap);
            continue;
        }
        Node cur = heap.top(); heap.pop();
        int s = cur.id;
        if (chosen[s]) continue;
        if (coverableCount[s] != cur.cnt || coverableCount[s] == 0) {
            // stale entry
            continue;
        }
        // choose this set
        chooseSet(s, heap);
    }

    // Build initial chosen list
    vector<int> chosenList;
    chosenList.reserve(m);
    for (int s = 1; s <= m; ++s) if (chosen[s]) chosenList.push_back(s);

    // If somehow not all covered (shouldn't happen), try a simple fallback: add cheapest covering sets for uncovered
    if (remainUncovered > 0) {
        // Build for each element the cheapest set covering it that isn't chosen
        for (int e = 1; e <= n; ++e) {
            if (uncovered[e]) {
                long long bestCost = LLONG_MAX;
                int bestSet = -1;
                for (int s : elemSets[e]) {
                    if (!chosen[s] && cost[s] < bestCost) {
                        bestCost = cost[s];
                        bestSet = s;
                    }
                }
                if (bestSet != -1) {
                    chosen[bestSet] = 1;
                    chosenList.push_back(bestSet);
                    // No need to update uncovered as final redundancy removal will verify coverage
                }
            }
        }
    }

    // Redundancy removal: remove any chosen set whose elements are still covered by others
    vector<int> coverCnt(n + 1, 0);
    for (int s : chosenList) {
        for (int e : setElems[s]) ++coverCnt[e];
    }
    // Sort chosen sets by descending cost, then by smaller set size
    vector<int> order = chosenList;
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (cost[a] != cost[b]) return cost[a] > cost[b];
        if (setElems[a].size() != setElems[b].size()) return setElems[a].size() > setElems[b].size();
        return a < b;
    });
    for (int s : order) {
        bool canRemove = true;
        for (int e : setElems[s]) {
            if (coverCnt[e] <= 1) { canRemove = false; break; }
        }
        if (canRemove) {
            for (int e : setElems[s]) --coverCnt[e];
            chosen[s] = 0;
        }
    }

    // Build final answer
    vector<int> ans;
    ans.reserve(m);
    for (int s = 1; s <= m; ++s) if (chosen[s]) ans.push_back(s);

    // Final verification: ensure each element is covered at least once; if not, add cheapest set covering missing element
    // This is a safety net to guarantee validity.
    fill(coverCnt.begin(), coverCnt.end(), 0);
    for (int s : ans) for (int e : setElems[s]) ++coverCnt[e];
    for (int e = 1; e <= n; ++e) {
        if (coverCnt[e] == 0) {
            long long bestCost = LLONG_MAX;
            int bestSet = -1;
            for (int s : elemSets[e]) {
                if (cost[s] < bestCost) {
                    bestCost = cost[s];
                    bestSet = s;
                }
            }
            if (bestSet != -1 && !chosen[bestSet]) {
                chosen[bestSet] = 1;
                ans.push_back(bestSet);
                for (int x : setElems[bestSet]) ++coverCnt[x];
            }
        }
    }

    // Output result
    cout << ans.size() << "\n";
    if (!ans.empty()) {
        for (size_t i = 0; i < ans.size(); ++i) {
            if (i) cout << ' ';
            cout << ans[i];
        }
    }
    cout << "\n";
    return 0;
}