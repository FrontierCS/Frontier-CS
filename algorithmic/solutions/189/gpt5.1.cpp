#include <iostream>
#include <string>

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    std::string s1, s2;
    if (!std::getline(std::cin, s1)) return 0;
    if (!std::getline(std::cin, s2)) s2 = "";

    // Remove possible '\r' if input has Windows-style line endings
    if (!s1.empty() && s1.back() == '\r') s1.pop_back();
    if (!s2.empty() && s2.back() == '\r') s2.pop_back();

    size_t n = s1.size();
    size_t m = s2.size();

    std::string T;
    T.reserve((n > m) ? n : m);

    size_t i = 0, j = 0;
    bool preferInsertOnTie = (m >= n);

    while (i < n && j < m) {
        if (s1[i] == s2[j]) {
            T.push_back('M');
            ++i;
            ++j;
        } else {
            bool insPossible = (j + 1 < m && s1[i] == s2[j + 1]);
            bool delPossible = (i + 1 < n && s1[i + 1] == s2[j]);

            if (insPossible && !delPossible) {
                T.push_back('I');
                ++j;
            } else if (delPossible && !insPossible) {
                T.push_back('D');
                ++i;
            } else if (insPossible && delPossible) {
                if (preferInsertOnTie) {
                    T.push_back('I');
                    ++j;
                } else {
                    T.push_back('D');
                    ++i;
                }
            } else {
                T.push_back('M');
                ++i;
                ++j;
            }
        }
    }

    while (i < n) {
        T.push_back('D');
        ++i;
    }
    while (j < m) {
        T.push_back('I');
        ++j;
    }

    std::cout << T << '\n';
    return 0;
}