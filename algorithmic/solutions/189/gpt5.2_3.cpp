#include <bits/stdc++.h>
using namespace std;

static void print_repeat(char c, size_t cnt) {
    const size_t BUF = 1 << 20; // 1 MiB
    string block(min(BUF, cnt), c);
    while (cnt > 0) {
        size_t take = min(cnt, block.size());
        cout.write(block.data(), (streamsize)take);
        cnt -= take;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) return 0;

    size_t n = s1.size(), m = s2.size();
    size_t common = min(n, m);

    print_repeat('M', common);
    if (n < m) print_repeat('I', m - n);
    else if (n > m) print_repeat('D', n - m);
    cout << '\n';
    return 0;
}