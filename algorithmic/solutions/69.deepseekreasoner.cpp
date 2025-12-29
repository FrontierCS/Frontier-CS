#include <bits/stdc++.h>
using namespace std;

struct SAM {
    struct State {
        int len, link;
        int next[2];
        State() : len(0), link(-1) {
            next[0] = next[1] = -1;
        }
    };
    vector<State> st;
    int sz, last;

    SAM(int maxLen) {
        st.reserve(2 * maxLen);
        init();
    }

    void init() {
        st.clear();
        st.emplace_back();
        sz = 1;
        last = 0;
    }

    void extend(int c) {
        int cur = sz++;
        st.emplace_back();
        st[cur].len = st[last].len + 1;
        int p = last;
        while (p != -1 && st[p].next[c] == -1) {
            st[p].next[c] = cur;
            p = st[p].link;
        }
        if (p == -1) {
            st[cur].link = 0;
        } else {
            int q = st[p].next[c];
            if (st[p].len + 1 == st[q].len) {
                st[cur].link = q;
            } else {
                int clone = sz++;
                st.emplace_back();
                st[clone].len = st[p].len + 1;
                st[clone].link = st[q].link;
                st[clone].next[0] = st[q].next[0];
                st[clone].next[1] = st[q].next[1];
                while (p != -1 && st[p].next[c] == q) {
                    st[p].next[c] = clone;
                    p = st[p].link;
                }
                st[q].link = st[cur].link = clone;
            }
        }
        last = cur;
    }

    long long distinct_substrings() {
        long long ans = 0;
        for (int i = 1; i < sz; ++i)
            ans += st[i].len - st[st[i].link].len;
        return ans;
    }
};

long long compute_power(const vector<int>& a, const vector<int>& b, SAM& sam) {
    sam.init();
    for (int x : a) sam.extend(x);
    for (int x : b) sam.extend(x);
    return sam.distinct_substrings();
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    int L = n;
    if (L < 700) L = 700;          // ensure enough range for distinct powers
    if (L > 30000) L = 30000;      // upper bound

    vector<string> words;
    vector<vector<int>> words_int;
    unordered_set<string> seen_words;
    unordered_set<long long> used_powers;
    vector<tuple<long long, int, int>> power_list;  // (power, u, v)

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist(0, 1);
    SAM sam(2 * L);

    for (int i = 0; i < n; ++i) {
        int attempts = 0;
        while (true) {
            ++attempts;
            if (attempts > 100) {       // if too many attempts, increase length slightly
                ++L;
                if (L > 30000) L = 30000;
                sam = SAM(2 * L);
                attempts = 0;
            }
            string w;
            vector<int> w_int;
            w.reserve(L);
            w_int.reserve(L);
            for (int j = 0; j < L; ++j) {
                int bit = dist(rng);
                w.push_back(bit ? 'O' : 'X');
                w_int.push_back(bit);
            }
            if (seen_words.count(w)) continue;

            bool collision = false;
            vector<tuple<long long, int, int>> new_powers;

            // check with itself
            long long p_self = compute_power(w_int, w_int, sam);
            if (used_powers.count(p_self)) {
                collision = true;
            } else {
                new_powers.emplace_back(p_self, i, i);
                // check with previous words
                for (int j = 0; j < i; ++j) {
                    long long p1 = compute_power(w_int, words_int[j], sam);
                    if (used_powers.count(p1)) {
                        collision = true;
                        break;
                    }
                    new_powers.emplace_back(p1, i, j);

                    long long p2 = compute_power(words_int[j], w_int, sam);
                    if (used_powers.count(p2)) {
                        collision = true;
                        break;
                    }
                    new_powers.emplace_back(p2, j, i);
                }
            }
            if (!collision) {
                // accept the word
                words.push_back(w);
                words_int.push_back(w_int);
                seen_words.insert(w);
                for (auto& [p, u, v] : new_powers) {
                    used_powers.insert(p);
                    power_list.emplace_back(p, u, v);
                }
                break;
            }
        }
    }

    // output the magic words
    for (string& w : words) {
        cout << w << '\n';
    }
    cout << flush;

    // prepare map for queries
    vector<pair<long long, pair<int, int>>> sorted_powers;
    sorted_powers.reserve(power_list.size());
    for (auto& [p, u, v] : power_list) {
        sorted_powers.emplace_back(p, make_pair(u + 1, v + 1)); // 1‑indexed
    }
    sort(sorted_powers.begin(), sorted_powers.end());

    int q;
    cin >> q;
    while (q--) {
        long long p;
        cin >> p;
        auto it = lower_bound(sorted_powers.begin(), sorted_powers.end(),
                              make_pair(p, make_pair(0, 0)));
        // it->first == p is guaranteed by the problem statement
        cout << it->second.first << ' ' << it->second.second << '\n';
        cout << flush;
    }

    return 0;
}