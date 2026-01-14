#include <iostream>

// Function to send a query and receive the response
double query(int x1, int y1, int x2, int y2) {
    std::cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << std::endl;
    double length;
    std::cin >> length;
    return length;
}

// Function to send the final answer
void answer(int x, int y, int r) {
    std::cout << "answer " << x << " " << y << " " << r << std::endl;
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    const int MAX_COORD = 100000;
    const double THRESHOLD = 1.0;

    // --- Find x-bounds ---

    // Find x_L_prime: the smallest x-coordinate with a significant chord length
    int x_L_prime = -1;
    int low = 0, high = MAX_COORD;
    while (low <= high) {
        int mid = low + (high - low) / 2;
        if (query(mid, 0, mid, MAX_COORD) > THRESHOLD) {
            x_L_prime = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }

    // Find x_R_prime: the largest x-coordinate with a significant chord length
    int x_R_prime = -1;
    low = x_L_prime; // Optimization: start search from x_L_prime
    high = MAX_COORD;
    while (low <= high) {
        int mid = low + (high - low) / 2;
        if (query(mid, 0, mid, MAX_COORD) > THRESHOLD) {
            x_R_prime = mid;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }

    // --- Find y-bounds ---

    // Find y_B_prime: the smallest y-coordinate with a significant chord length
    int y_B_prime = -1;
    low = 0, high = MAX_COORD;
    while (low <= high) {
        int mid = low + (high - low) / 2;
        if (query(0, mid, MAX_COORD, mid) > THRESHOLD) {
            y_B_prime = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }

    // Find y_T_prime: the largest y-coordinate with a significant chord length
    int y_T_prime = -1;
    low = y_B_prime; // Optimization: start search from y_B_prime
    high = MAX_COORD;
    while (low <= high) {
        int mid = low + (high - low) / 2;
        if (query(0, mid, MAX_COORD, mid) > THRESHOLD) {
            y_T_prime = mid;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }

    // --- Calculate center and radius ---
    
    int center_x = (x_L_prime + x_R_prime) / 2;
    int center_y = (y_B_prime + y_T_prime) / 2;
    int radius = (x_R_prime - x_L_prime) / 2 + 1;
    
    answer(center_x, center_y, radius);

    return 0;
}