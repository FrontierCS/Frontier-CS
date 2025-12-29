#include <iostream>

// Helper function to send a query and receive the response.
double ask(int x1, int y1, int x2, int y2) {
    std::cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << std::endl;
    double response;
    std::cin >> response;
    return response;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int y_b, y_t, x_l, x_r;
    const double EPS = 1e-9; // Epsilon for floating point comparison with zero.

    // Binary search for y_bottom: the smallest y with a non-zero intersection.
    {
        int l = 0, r = 100000, ans = 100001;
        while (l <= r) {
            int mid = l + (r - l) / 2;
            if (ask(0, mid, 100000, mid) > EPS) {
                ans = mid;
                r = mid - 1;
            } else {
                l = mid + 1;
            }
        }
        y_b = ans;
    }

    // Binary search for y_top: the largest y with a non-zero intersection.
    {
        int l = 0, r = 100000, ans = -1;
        while (l <= r) {
            int mid = l + (r - l) / 2;
            if (ask(0, mid, 100000, mid) > EPS) {
                ans = mid;
                l = mid + 1;
            } else {
                r = mid - 1;
            }
        }
        y_t = ans;
    }

    // Binary search for x_left: the smallest x with a non-zero intersection.
    {
        int l = 0, r = 100000, ans = 100001;
        while (l <= r) {
            int mid = l + (r - l) / 2;
            if (ask(mid, 0, mid, 100000) > EPS) {
                ans = mid;
                r = mid - 1;
            } else {
                l = mid + 1;
            }
        }
        x_l = ans;
    }

    // Binary search for x_right: the largest x with a non-zero intersection.
    {
        int l = 0, r = 100000, ans = -1;
        while (l <= r) {
            int mid = l + (r - l) / 2;
            if (ask(mid, 0, mid, 100000) > EPS) {
                ans = mid;
                l = mid + 1;
            } else {
                r = mid - 1;
            }
        }
        x_r = ans;
    }
    
    // Calculate center and radius from the extremal coordinates.
    int cx = (x_l + x_r) / 2;
    int cy = (y_b + y_t) / 2;
    int r_val = (x_r - x_l + 2) / 2;

    // Output the final answer.
    std::cout << "answer " << cx << " " << cy << " " << r_val << std::endl;

    return 0;
}