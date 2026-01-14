#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cassert>

char query(int i, int j) {
    std::cout << "? " << i << " " << j << std::endl;
    char response;
    std::cin >> response;
    return response;
}

void solve() {
    int n;
    std::cin >> n;

    std::vector<int> p(n);
    std::iota(p.begin(), p.end(), 1);

    std::vector<int> ans(n + 1, 0);
    int current_val = n;

    while (p.size() > 2) {
        int i1 = p.back();
        int i2 = p[p.size() - 2];
        int i3 = p[p.size() - 3];

        int min_idx, mid_idx, max_idx;

        char r12 = query(i1, i2);
        if (r12 == '<') { // a[i1] < a[i2]
            char r23 = query(i2, i3);
            if (r23 == '<') { // a[i1] < a[i2] < a[i3]
                min_idx = i1; mid_idx = i2; max_idx = i3;
            } else { // a[i2] > a[i3]
                char r13 = query(i1, i3);
                if (r13 == '<') { // a[i1] < a[i3] < a[i2]
                    min_idx = i1; mid_idx = i3; max_idx = i2;
                } else { // a[i3] < a[i1] < a[i2]
                    min_idx = i3; mid_idx = i1; max_idx = i2;
                }
            }
        } else { // a[i1] > a[i2]
            char r23 = query(i2, i3);
            if (r23 == '>') { // a[i1] > a[i2] > a[i3]
                min_idx = i3; mid_idx = i2; max_idx = i1;
            } else { // a[i2] < a[i3]
                char r13 = query(i1, i3);
                if (r13 == '<') { // a[i2] < a[i1] < a[i3]
                    min_idx = i2; mid_idx = i1; max_idx = i3;
                } else { // a[i2] < a[i3] < a[i1]
                    min_idx = i2; mid_idx = i3; max_idx = i1;
                }
            }
        }
        
        ans[max_idx] = current_val;
        ans[mid_idx] = current_val - 1;
        current_val -= 2;

        p.pop_back();
        p.pop_back();
        p.pop_back();
        p.push_back(min_idx);
        std::sort(p.begin(), p.end());
    }

    if (p.size() == 2) {
        char res = query(p[0], p[1]);
        if (res == '<') {
            ans[p[0]] = 1;
            ans[p[1]] = 2;
        } else {
            ans[p[0]] = 2;
            ans[p[1]] = 1;
        }
    } else if (p.size() == 1) {
        ans[p[0]] = 1;
    }
    
    std::cout << "!";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << ans[i];
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}