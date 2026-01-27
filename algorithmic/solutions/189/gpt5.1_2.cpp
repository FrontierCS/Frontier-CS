#include <iostream>
#include <string>

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    std::string s1, s2;
    if (!(std::cin >> s1)) return 0;
    if (!(std::cin >> s2)) s2.clear();

    size_t n = s1.size();
    size_t m = s2.size();

    std::string T;
    T.reserve(n + m);

    if (n <= m) {
        T.append(n, 'M');
        T.append(m - n, 'I');
    } else {
        T.append(m, 'M');
        T.append(n - m, 'D');
    }

    std::cout << T << '\n';
    return 0;
}