#include <bits/stdc++.h>
using namespace std;

int n, k;

vector<pair<int, int>> ask(int x, int y, int z) {
    cout << "? " << x << " " << y << " " << z << endl;
    cout.flush();
    int r;
    cin >> r;
    vector<pair<int, int>> res;
    for (int i = 0; i < r; ++i) {
        int a, b;
        cin >> a >> b;
        if (a > b) swap(a, b);
        res.emplace_back(a, b);
    }
    return res;
}

bool has_pair(int a, int b, const vector<pair<int, int>>& res) {
    if (a > b) swap(a, b);
    for (auto& p : res)
        if (p.first == a && p.second == b)
            return true;
    return false;
}

pair<int, int> find_adjacent_pair(int start) {
    vector<int> candidates;
    for (int i = 0; i < n; ++i)
        if (i != start)
            candidates.push_back(i);

    while (candidates.size() > 2) {
        vector<int> next_cand;
        for (size_t i = 0; i < candidates.size(); i += 2) {
            if (i + 1 == candidates.size()) {
                next_cand.push_back(candidates[i]);
                continue;
            }
            int b = candidates[i], c = candidates[i + 1];
            auto res = ask(start, b, c);
            bool ab = has_pair(start, b, res);
            bool ac = has_pair(start, c, res);
            if (ab && !ac)
                next_cand.push_back(b);
            else if (!ab && ac)
                next_cand.push_back(c);
            else if (ab && ac) {
                next_cand.push_back(b);
                next_cand.push_back(c);
            }
            // else discard both
        }
        if (candidates.size() == next_cand.size())
            break;
        candidates = move(next_cand);
    }

    if (candidates.size() > 2) {
        // fallback: take first two
        return {candidates[0], candidates[1]};
    }
    return {candidates[0], candidates[1]};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> k >> n;

    // find an adjacent pair starting from door 0
    auto [a, b] = find_adjacent_pair(0);
    deque<int> dq = {0, a};  // assume 0 and a are consecutive; b is the other neighbor of 0
    // we will use b later to verify direction, but for simplicity we start with this chain.

    vector<bool> used(n, false);
    used[0] = used[a] = true;
    vector<int> unused;
    for (int i = 0; i < n; ++i)
        if (!used[i])
            unused.push_back(i);
    random_shuffle(unused.begin(), unused.end());

    // extend the chain from both ends
    while (dq.size() < n) {
        // front
        int front = dq.front();
        int front_next = *(dq.begin() + 1);
        bool extended = false;
        for (size_t i = 0; i < unused.size(); ++i) {
            int x = unused[i];
            auto res = ask(front, front_next, x);
            if (has_pair(front, x, res)) {
                dq.push_front(x);
                used[x] = true;
                unused.erase(unused.begin() + i);
                extended = true;
                break;
            }
        }
        if (extended) continue;

        // back
        int back = dq.back();
        int back_prev = *(dq.rbegin() + 1);
        for (size_t i = 0; i < unused.size(); ++i) {
            int x = unused[i];
            auto res = ask(back, back_prev, x);
            if (has_pair(back, x, res)) {
                dq.push_back(x);
                used[x] = true;
                unused.erase(unused.begin() + i);
                extended = true;
                break;
            }
        }
        if (!extended) {
            // fallback: append the first unused door (should not happen)
            dq.push_back(unused[0]);
            unused.erase(unused.begin());
        }
    }

    vector<int> order(dq.begin(), dq.end());
    cout << "! ";
    for (int x : order)
        cout << x << " ";
    cout << endl;
    cout.flush();

    return 0;
}