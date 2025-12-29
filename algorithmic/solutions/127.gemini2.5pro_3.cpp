#include <iostream>
#include <utility>
#include <vector>

// Function to ask a query for box i
std::pair<int, int> ask(int i) {
    std::cout << "? " << i << std::endl;
    int a0, a1;
    std::cin >> a0 >> a1;
    return {a0, a1};
}

// Function to submit the final answer
void answer(int i) {
    std::cout << "! " << i << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    int l = 0, r = n - 1;
    
    while (l < r) {
        int mid = l + (r - l) / 2;
        auto res = ask(mid);
        int a0 = res.first;
        int a1 = res.second;
        int s = a0 + a1;

        if (s == 0) {
            answer(mid);
            return 0;
        }

        if (s == 1) {
            if (a0 == 1) {
                r = mid - 1;
            } else { // a1 == 1
                l = mid + 1;
            }
        } else { // s > 1
            if (a0 >= a1) {
                r = mid - 1;
            } else {
                l = mid + 1;
            }
        }
    }

    answer(l);

    return 0;
}