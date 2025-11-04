/**
 * Simple lightweight chart library for Business Dashboard
 * Provides basic line and bar charts without external dependencies
 */

class SimpleChart {
    constructor(canvasId, options) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            console.error(`Canvas with id ${canvasId} not found`);
            return;
        }
        this.ctx = this.canvas.getContext('2d');
        this.options = options;
        this.data = options.data;
        this.type = options.type || 'line';
        
        // Set canvas size
        const rect = this.canvas.getBoundingClientRect();
        this.canvas.width = rect.width;
        this.canvas.height = rect.height || 300;
        
        this.draw();
    }
    
    draw() {
        if (this.type === 'line') {
            this.drawLineChart();
        } else if (this.type === 'bar') {
            this.drawBarChart();
        }
    }
    
    drawLineChart() {
        const padding = 50;
        const width = this.canvas.width - padding * 2;
        const height = this.canvas.height - padding * 2;
        
        const labels = this.data.labels;
        const dataset = this.data.datasets[0];
        const dataValues = dataset.data;
        
        if (!dataValues || dataValues.length === 0) {
            this.drawNoData();
            return;
        }
        
        // Calculate scales
        const maxValue = Math.max(...dataValues);
        const minValue = 0;
        const valueRange = maxValue - minValue || 1;
        
        // Draw axes
        this.ctx.strokeStyle = '#e0e6ed';
        this.ctx.lineWidth = 2;
        
        // Y-axis
        this.ctx.beginPath();
        this.ctx.moveTo(padding, padding);
        this.ctx.lineTo(padding, this.canvas.height - padding);
        this.ctx.stroke();
        
        // X-axis
        this.ctx.beginPath();
        this.ctx.moveTo(padding, this.canvas.height - padding);
        this.ctx.lineTo(this.canvas.width - padding, this.canvas.height - padding);
        this.ctx.stroke();
        
        // Draw grid lines
        this.ctx.strokeStyle = '#f0f0f0';
        this.ctx.lineWidth = 1;
        for (let i = 0; i <= 5; i++) {
            const y = padding + (height / 5) * i;
            this.ctx.beginPath();
            this.ctx.moveTo(padding, y);
            this.ctx.lineTo(this.canvas.width - padding, y);
            this.ctx.stroke();
        }
        
        // Draw Y-axis labels
        this.ctx.fillStyle = '#7f8c8d';
        this.ctx.font = '12px sans-serif';
        this.ctx.textAlign = 'right';
        for (let i = 0; i <= 5; i++) {
            const value = maxValue - (maxValue / 5) * i;
            const y = padding + (height / 5) * i;
            this.ctx.fillText(Math.round(value), padding - 10, y + 4);
        }
        
        // Plot data points and line
        const stepX = width / (dataValues.length - 1 || 1);
        
        // Draw line
        this.ctx.strokeStyle = dataset.borderColor || '#3498db';
        this.ctx.lineWidth = 3;
        this.ctx.beginPath();
        
        dataValues.forEach((value, index) => {
            const x = padding + stepX * index;
            const y = this.canvas.height - padding - ((value - minValue) / valueRange) * height;
            
            if (index === 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }
        });
        this.ctx.stroke();
        
        // Draw fill area
        if (dataset.fill) {
            this.ctx.lineTo(padding + stepX * (dataValues.length - 1), this.canvas.height - padding);
            this.ctx.lineTo(padding, this.canvas.height - padding);
            this.ctx.closePath();
            this.ctx.fillStyle = dataset.backgroundColor || 'rgba(52, 152, 219, 0.1)';
            this.ctx.fill();
        }
        
        // Draw points
        this.ctx.fillStyle = dataset.borderColor || '#3498db';
        dataValues.forEach((value, index) => {
            const x = padding + stepX * index;
            const y = this.canvas.height - padding - ((value - minValue) / valueRange) * height;
            
            this.ctx.beginPath();
            this.ctx.arc(x, y, 5, 0, Math.PI * 2);
            this.ctx.fill();
            
            // White border
            this.ctx.strokeStyle = '#fff';
            this.ctx.lineWidth = 2;
            this.ctx.stroke();
        });
        
        // Draw X-axis labels
        this.ctx.fillStyle = '#7f8c8d';
        this.ctx.font = '11px sans-serif';
        this.ctx.textAlign = 'center';
        labels.forEach((label, index) => {
            const x = padding + stepX * index;
            const y = this.canvas.height - padding + 20;
            // Show every nth label to avoid crowding
            if (labels.length <= 10 || index % Math.ceil(labels.length / 10) === 0) {
                this.ctx.fillText(label, x, y);
            }
        });
        
        // Draw title
        if (this.options.options && this.options.options.scales) {
            this.ctx.fillStyle = '#2c3e50';
            this.ctx.font = 'bold 14px sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.fillText(dataset.label || 'Chart', this.canvas.width / 2, 20);
        }
    }
    
    drawBarChart() {
        const padding = 50;
        const width = this.canvas.width - padding * 2;
        const height = this.canvas.height - padding * 2;
        
        const labels = this.data.labels;
        const dataset = this.data.datasets[0];
        const dataValues = dataset.data;
        
        if (!dataValues || dataValues.length === 0) {
            this.drawNoData();
            return;
        }
        
        // Calculate scales
        const maxValue = Math.max(...dataValues);
        const minValue = 0;
        const valueRange = maxValue - minValue || 1;
        
        // Draw axes
        this.ctx.strokeStyle = '#e0e6ed';
        this.ctx.lineWidth = 2;
        
        // Y-axis
        this.ctx.beginPath();
        this.ctx.moveTo(padding, padding);
        this.ctx.lineTo(padding, this.canvas.height - padding);
        this.ctx.stroke();
        
        // X-axis
        this.ctx.beginPath();
        this.ctx.moveTo(padding, this.canvas.height - padding);
        this.ctx.lineTo(this.canvas.width - padding, this.canvas.height - padding);
        this.ctx.stroke();
        
        // Draw grid lines
        this.ctx.strokeStyle = '#f0f0f0';
        this.ctx.lineWidth = 1;
        for (let i = 0; i <= 5; i++) {
            const y = padding + (height / 5) * i;
            this.ctx.beginPath();
            this.ctx.moveTo(padding, y);
            this.ctx.lineTo(this.canvas.width - padding, y);
            this.ctx.stroke();
        }
        
        // Draw Y-axis labels
        this.ctx.fillStyle = '#7f8c8d';
        this.ctx.font = '12px sans-serif';
        this.ctx.textAlign = 'right';
        for (let i = 0; i <= 5; i++) {
            const value = maxValue - (maxValue / 5) * i;
            const y = padding + (height / 5) * i;
            this.ctx.fillText(Math.round(value), padding - 10, y + 4);
        }
        
        // Draw bars
        const barWidth = (width / dataValues.length) * 0.7;
        const barSpacing = (width / dataValues.length) * 0.3;
        
        dataValues.forEach((value, index) => {
            const x = padding + (width / dataValues.length) * index + barSpacing / 2;
            const barHeight = ((value - minValue) / valueRange) * height;
            const y = this.canvas.height - padding - barHeight;
            
            // Draw bar
            this.ctx.fillStyle = dataset.backgroundColor || 'rgba(52, 152, 219, 0.7)';
            this.ctx.fillRect(x, y, barWidth, barHeight);
            
            // Draw border
            this.ctx.strokeStyle = dataset.borderColor || '#3498db';
            this.ctx.lineWidth = 2;
            this.ctx.strokeRect(x, y, barWidth, barHeight);
        });
        
        // Draw X-axis labels
        this.ctx.fillStyle = '#7f8c8d';
        this.ctx.font = '11px sans-serif';
        this.ctx.textAlign = 'center';
        labels.forEach((label, index) => {
            const x = padding + (width / dataValues.length) * index + (width / dataValues.length) / 2;
            const y = this.canvas.height - padding + 20;
            // Show every nth label to avoid crowding
            if (labels.length <= 10 || index % Math.ceil(labels.length / 10) === 0) {
                this.ctx.fillText(label, x, y);
            }
        });
        
        // Draw title
        this.ctx.fillStyle = '#2c3e50';
        this.ctx.font = 'bold 14px sans-serif';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(dataset.label || 'Chart', this.canvas.width / 2, 20);
    }
    
    drawNoData() {
        this.ctx.fillStyle = '#7f8c8d';
        this.ctx.font = '16px sans-serif';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('No data available', this.canvas.width / 2, this.canvas.height / 2);
    }
}

// Make it available globally
window.SimpleChart = SimpleChart;
