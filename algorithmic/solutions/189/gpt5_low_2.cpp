#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) return 0;

    size_t n = s1.size(), m = s2.size();
    size_t k = min(n, m);
    size_t rem = (n > m) ? (n - m) : (m - n);
    char extra = (m > n) ? 'I' : 'D';

    auto write_chars = [](char c, size_t cnt) {
        const size_t BLOCK = 1 << 20; // 1,048,576
        string block(min(cnt, BLOCK), c);
        while (cnt) {
            size_t take = min(cnt, BLOCK);
            if (block.size() != take) block.assign(take, c);
            cout.write(block.data(), take);
            cnt -= take;
        }
    };

    write_chars('M', k);
    if (rem) write_chars(extra, rem);
    cout << '\n';
    return 0;
}