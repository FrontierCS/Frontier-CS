#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <algorithm>
#include <cstdlib>
#include <cstring>

using namespace std;

struct State {
    int len, link;
    int next[2];
    State() : len(0), link(-1) {
        next[0] = next[1] = -1;
    }
};

long long distinct_substrings(const string& s) {
    vector<State> st;
    st.emplace_back();
    int last = 0;
    for (char c : s) {
        int idx = (c == 'X') ? 0 : 1;
        int cur = st.size();
        st.emplace_back();
        st[cur].len = st[last].len + 1;
        int p = last;
        while (p != -1 && st[p].next[idx] == -1) {
            st[p].next[idx] = cur;
            p = st[p].link;
        }
        if (p == -1) {
            st[cur].link = 0;
        } else {
            int q = st[p].next[idx];
            if (st[p].len + 1 == st[q].len) {
                st[cur].link = q;
            } else {
                int clone = st.size();
                st.push_back(st[q]);
                st[clone].len = st[p].len + 1;
                while (p != -1 && st[p].next[idx] == q) {
                    st[p].next[idx] = clone;
                    p = st[p].link;
                }
                st[q].link = st[cur].link = clone;
            }
        }
        last = cur;
    }
    long long ans = 0;
    for (size_t i = 1; i < st.size(); ++i) {
        ans += st[i].len - st[st[i].link].len;
    }
    return ans;
}

string to_binary(long long x, int L) {
    string s(L, 'X');
    for (int k = L-1; k >= 0; --k) {
        if (x & 1) s[k] = 'O';
        x >>= 1;
    }
    return s;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    vector<string> words;
    unordered_set<long long> used_powers;
    unordered_map<long long, pair<int,int>> power_to_pair;

    int L = 10;
    long long counter = 0;

    for (int i = 0; i < n; ++i) {
        bool found = false;
        int tries = 0;
        while (!found && tries < 100) {
            string w = to_binary(counter, L);
            counter++;
            tries++;

            bool distinct = true;
            for (const string& prev : words) {
                if (w == prev) {
                    distinct = false;
                    break;
                }
            }
            if (!distinct) continue;

            vector<long long> new_powers;
            bool ok = true;

            for (int j = 0; j < i; ++j) {
                long long p1 = distinct_substrings(w + words[j]);
                long long p2 = distinct_substrings(words[j] + w);
                new_powers.push_back(p1);
                new_powers.push_back(p2);
            }
            long long p_self = distinct_substrings(w + w);
            new_powers.push_back(p_self);

            unordered_set<long long> temp;
            for (long long p : new_powers) {
                if (temp.count(p) || used_powers.count(p)) {
                    ok = false;
                    break;
                }
                temp.insert(p);
            }
            if (!ok) continue;

            words.push_back(w);
            for (int j = 0; j < i; ++j) {
                long long p1 = distinct_substrings(w + words[j]);
                long long p2 = distinct_substrings(words[j] + w);
                used_powers.insert(p1);
                used_powers.insert(p2);
                power_to_pair[p1] = {i, j};
                power_to_pair[p2] = {j, i};
            }
            used_powers.insert(p_self);
            power_to_pair[p_self] = {i, i};
            found = true;
        }
        if (!found) {
            L++;
            counter = 0;
            i--;
        }
    }

    for (const string& w : words) {
        cout << w << '\n';
    }
    cout << flush;

    int q;
    cin >> q;
    while (q--) {
        long long p;
        cin >> p;
        auto it = power_to_pair.find(p);
        pair<int,int> idx = it->second;
        cout << idx.first+1 << ' ' << idx.second+1 << '\n';
        cout << flush;
    }

    return 0;
}