/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FloatField } from "@web/views/fields/float/float_field";

// Helper function để format số với dấu chấm phân tách hàng ngàn
function formatVNDNumber(value) {
    if (value === false || value === null || value === undefined) {
        return "0";
    }
    const intValue = Math.round(value);
    return intValue.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

// Thêm global functions để sử dụng trong templates (nếu cần)
window.formatVND = formatVNDNumber;

// Widget tiền VNĐ đẹp - loại bỏ số thập phân và format đẹp hơn
class VNDCurrencyField extends FloatField {
    
    formatValue(value) {
        if (value === false || value === null || value === undefined) {
            return "";
        }
        return formatVNDNumber(value) + " ₫";
    }

    get formattedValue() {
        const value = this.props.record.data[this.props.name];
        return this.formatValue(value);
    }
}

// Widget số đẹp - format số thông thường với dấu chấm phân tách
class NumberField extends FloatField {
    
    formatValue(value) {
        if (value === false || value === null || value === undefined) {
            return "";
        }
        
        // Giữ nguyên số thập phân nếu có, chỉ format dấu phân tách hàng nghìn
        if (value % 1 === 0) {
            // Số nguyên - không có phần thập phân
            return value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
        } else {
            // Số thập phân - format và giữ tối đa 2 chữ số thập phân
            return value.toFixed(2).replace(/\.?0+$/, '').replace(/\B(?=(\d{3})+(?!\d))/g, ".");
        }
    }

    get formattedValue() {
        const value = this.props.record.data[this.props.name];
        return this.formatValue(value);
    }
}

// Đăng ký widgets
registry.category("fields").add("vnd_currency", {
    component: VNDCurrencyField,
});

registry.category("fields").add("number_format", {
    component: NumberField,
});