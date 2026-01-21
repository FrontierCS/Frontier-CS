#include <bits/stdc++.h>
using namespace std;

static int N, M;
static std::mt19937 rng(712367);

static inline void appendInt(string &s, int x) {
    char buf[16];
    int len = 0;
    if (x == 0) {
        buf[len++] = '0';
    } else {
        while (x > 0) {
            buf[len++] = char('0' + (x % 10));
            x /= 10;
        }
    }
    for (int i = len - 1; i >= 0; --i) s.push_back(buf[i]);
}

static int query_without(const vector<int> &v, int skip_pos) {
    int k = (int)v.size() - 1;
    string out;
    out.reserve(3 + (size_t)k * 6);
    out.push_back('?');
    out.push_back(' ');
    appendInt(out, k);
    for (int i = 0; i < (int)v.size(); i++) {
        if (i == skip_pos) continue;
        out.push_back(' ');
        appendInt(out, v[i]);
    }
    out.push_back('\n');
    cout.write(out.data(), (streamsize)out.size());
    cout.flush();

    int ans;
    if (!(cin >> ans)) exit(0);
    return ans;
}

static void output_stick(const vector<int> &stick) {
    string out;
    out.reserve(3 + (size_t)stick.size() * 6);
    out.push_back('!');
    for (int x : stick) {
        out.push_back(' ');
        appendInt(out, x);
    }
    out.push_back('\n');
    cout.write(out.data(), (streamsize)out.size());
    cout.flush();
}

static pair<vector<int>, vector<int>> split_group(vector<int> items, int a) {
    const int target = a * N;
    vector<int> removed;
    removed.reserve(items.size() - (size_t)target);

    std::shuffle(items.begin(), items.end(), rng);

    int p = 0;
    while ((int)items.size() > target) {
        if (p >= (int)items.size()) {
            // Should not happen if interaction is consistent, but avoid infinite loops.
            p = 0;
        }
        int ans = query_without(items, p);
        if (ans >= a) {
            int cand = items[p];
            removed.push_back(cand);
            items[p] = items.back();
            items.pop_back();
            // p unchanged (new element at p is unprocessed)
        } else {
            ++p;
        }
    }
    return {std::move(items), std::move(removed)};
}

static void solve(vector<int> items, int m) {
    if (m == 1) {
        output_stick(items);
        return;
    }
    int a = m / 2;
    int b = m - a;

    auto [left, right] = split_group(std::move(items), a);
    solve(std::move(left), a);
    solve(std::move(right), b);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> M;
    int L = N * M;

    if (M == 1) {
        vector<int> stick(N);
        iota(stick.begin(), stick.end(), 1);
        output_stick(stick);
        return 0;
    }

    vector<int> all(L);
    iota(all.begin(), all.end(), 1);

    solve(std::move(all), M);
    return 0;
}